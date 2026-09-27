from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.wrappers.response import Response

try:
    from ..extensions import db
    from ..forms import CalendarEventForm
    from ..models import CalendarEvent, CalendarEventType, User
    from ..services.calendar_notifications import (
        notify_event_created,
        notify_event_deleted,
        notify_event_updated,
    )
except ImportError:
    from extensions import db
    from forms import CalendarEventForm
    from models import CalendarEvent, CalendarEventType, User
    from services.calendar_notifications import (
        notify_event_created,
        notify_event_deleted,
        notify_event_updated,
    )

calendar = Blueprint("calendar", __name__)

MONTH_NAMES: list[str] = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]  # fmt: skip

# Calendar grid starts the week on Sunday.
_CAL = calendar_module.Calendar(firstweekday=6)


def _normalize_year_month(year: int, month: int) -> tuple[int, int]:
    """Roll an out-of-range month (e.g. 13, 0, -1) into the correct year."""
    index: int = year * 12 + (month - 1)
    return index // 12, index % 12 + 1


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    return _normalize_year_month(year, month + delta)


def _get_or_create_event_type_id(name: str | None) -> int | None:
    """Look up a CalendarEventType by name (case-insensitive), creating it
    if it doesn't exist yet. Returns None for a blank/missing name."""
    name = (name or "").strip()
    if not name:
        return None

    existing: CalendarEventType | None = CalendarEventType.query.filter(
        db.func.lower(CalendarEventType.event_type) == name.lower()
    ).first()
    if existing:
        return existing.id

    new_type = CalendarEventType(event_type=name)
    db.session.add(new_type)
    db.session.flush()  # assign new_type.id without committing yet
    return new_type.id


def _calendar_context(year: int, month: int) -> dict:
    """Shared query logic for rendering a month grid: which dates belong
    to the grid (including the leading/trailing days of the adjacent
    months needed to fill out full weeks), and which events fall on each
    of those dates."""
    year, month = _normalize_year_month(year, month)

    weeks: list[list[date]] = _CAL.monthdatescalendar(year, month)
    grid_start: date = weeks[0][0]
    grid_end: date = weeks[-1][-1]

    range_start: datetime = datetime.combine(grid_start, datetime.min.time())
    range_end: datetime = datetime.combine(
        grid_end + timedelta(days=1), datetime.min.time()
    )

    events: list[CalendarEvent] = (
        CalendarEvent.query.filter(
            CalendarEvent.start_time >= range_start,
            CalendarEvent.start_time < range_end,
        )
        .order_by(CalendarEvent.start_time)
        .all()
    )

    events_by_day: dict[date, list[CalendarEvent]] = {}
    for event in events:
        events_by_day.setdefault(event.start_time.date(), []).append(event)

    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)

    event_type_names: list[str] = [
        event_type.event_type
        for event_type in CalendarEventType.query.order_by(
            CalendarEventType.event_type
        ).all()
        if event_type.event_type
    ]

    return {
        "weeks": weeks,
        "events_by_day": events_by_day,
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES[month - 1],
        "today": datetime.now(tz=timezone.utc),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "event_type_names": event_type_names,
    }


def _acting_user() -> User:
    """Look up the logged-in user's actual `User` row. `current_user` from
    Flask-Login is a proxy, not a `User` instance, so anything that needs
    a real `User` object (notifications, `.username`) goes through this --
    same pattern used in the complaints blueprint."""
    user: User | None = User.query.filter(User.id == current_user.id).first()
    if user is None:
        raise ValueError("Logged-in user does not exist in the database")
    return user


def _get_year_month_args() -> tuple[int, int]:
    today: date = datetime.now(tz=timezone.utc)
    year: int = request.args.get("year", today.year, type=int) or today.year
    month: int = request.args.get("month", today.month, type=int) or today.month
    return year, month


@calendar.route("/calendar")
@login_required
def index() -> str:
    year, month = _get_year_month_args()
    context = _calendar_context(year, month)
    context["form"] = CalendarEventForm()
    return render_template("calendar.html", **context)


@calendar.route("/calendar/events/new", methods=["POST"])
@login_required
def new_event() -> tuple[str, int] | Response:
    """Create a new calendar event. Either user can add events to the
    shared calendar -- there's no per-user ownership on creation, only
    `created_by` is recorded for notification/attribution purposes."""

    form = CalendarEventForm()
    if form.validate_on_submit():
        # DataRequired guarantees this is populated once validation passes.
        start_time: datetime = form.start_time.data  # type: ignore[assignment]

        acting_user: User = _acting_user()
        event = CalendarEvent(
            title=form.title.data or "",
            description=form.description.data or None,
            event_type_id=_get_or_create_event_type_id(form.event_type.data),
            is_all_day=bool(form.is_all_day.data),
            start_time=start_time,
            end_time=form.end_time.data or None,
            created_by=acting_user.id,
        )
        db.session.add(event)
        db.session.commit()
        notify_event_created(event, created_by=acting_user)
        flash("Event added", "info")
        return redirect(
            url_for("calendar.index", year=start_time.year, month=start_time.month)
        )

    # Validation failed: re-render the month the user was adding an event
    # to, with the entered data and errors preserved and the modal
    # reopened, instead of silently discarding what they typed.
    fallback: date = form.start_time.data or datetime.now(tz=timezone.utc)
    context = _calendar_context(fallback.year, fallback.month)
    context["form"] = form
    context["open_modal"] = True
    return render_template("calendar.html", **context), 400


@calendar.route("/calendar/events/<int:event_id>/edit", methods=["POST"])
@login_required
def edit_event(event_id: int) -> Response:
    """Edit an existing event. Both users can edit any event -- this is a
    shared calendar, not adversarial content like a complaint, so there's
    no ownership restriction here (unlike `delete`, below)."""

    event: CalendarEvent = CalendarEvent.query.get_or_404(event_id)

    form = CalendarEventForm()
    if not form.validate_on_submit():
        errors: str = "; ".join(
            f"{getattr(form, field).label.text}: {', '.join(messages)}"
            for field, messages in form.errors.items()
        )
        flash(f"Could not update event -- {errors}", "danger")
        return redirect(
            url_for(
                "calendar.index",
                year=event.start_time.year,
                month=event.start_time.month,
            )
        )

    event.title = form.title.data or ""
    event.description = form.description.data or None
    event.event_type_id = _get_or_create_event_type_id(form.event_type.data)
    event.is_all_day = bool(form.is_all_day.data)
    # DataRequired guarantees this is populated once validation passes.
    start_time: datetime = form.start_time.data  # type: ignore[assignment]
    event.start_time = start_time
    event.end_time = form.end_time.data or None
    db.session.commit()

    notify_event_updated(event, updated_by=_acting_user())
    flash("Event updated", "info")
    return redirect(
        url_for("calendar.index", year=start_time.year, month=start_time.month)
    )


@calendar.route("/calendar/events/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id: int) -> Response:
    """Delete an event. Restricted to whoever created it, matching the
    pattern used for deleting complaints."""

    event: CalendarEvent = CalendarEvent.query.get_or_404(event_id)
    acting_user: User = _acting_user()

    if event.created_by != acting_user.id:
        flash("Only the person who added an event can delete it", "danger")
        return redirect(
            url_for(
                "calendar.index",
                year=event.start_time.year,
                month=event.start_time.month,
            )
        )

    year, month, title = event.start_time.year, event.start_time.month, event.title
    db.session.delete(event)
    db.session.commit()

    notify_event_deleted(title, deleted_by=acting_user)
    flash("Event deleted", "info")
    return redirect(url_for("calendar.index", year=year, month=month))
