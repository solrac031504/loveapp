"""Notification triggers for calendar events.

LoveApp is built for exactly one couple (see `create-user` in app.py --
there's no self-service signup), so "the other user" is simply whichever
User row isn't the one who took the action.
"""

from __future__ import annotations

try:
    from ..models import CalendarEvent, User
    from .notifier import notify
except ImportError:
    from models import CalendarEvent, User
    from services.notifier import notify


def _other_user(user_id: int) -> User | None:
    return User.query.filter(User.id != user_id).first()


def _format_when(event: CalendarEvent) -> str:
    if event.is_all_day:
        return f"{event.start_time.strftime('%b %d, %Y')} (all day)"

    when: str = event.start_time.strftime("%b %d, %Y %I:%M %p")
    if event.end_time:
        when += f" - {event.end_time.strftime('%I:%M %p')}"
    return when


def notify_event_created(event: CalendarEvent, created_by: User) -> None:
    """Tell the other user a new event was added to the shared calendar."""
    recipient: User | None = _other_user(created_by.id)
    if recipient is None:
        return

    subject: str = f"New event: {event.title}"
    message: str = (
        f'{created_by.username} added a new calendar event: "{event.title}"\n\n'
        f"When: {_format_when(event)}"
    )
    if event.description:
        message += f"\n\n{event.description}"

    notify(recipient, subject, message, notif_type="event")


def notify_event_updated(event: CalendarEvent, updated_by: User) -> None:
    """Tell the other user an event was changed."""
    recipient: User | None = _other_user(updated_by.id)
    if recipient is None:
        return

    subject: str = f"Event updated: {event.title}"
    message: str = (
        f'{updated_by.username} updated the calendar event "{event.title}"\n\n'
        f"When: {_format_when(event)}"
    )

    notify(recipient, subject, message, notif_type="event")


def notify_event_deleted(event_title: str, deleted_by: User) -> None:
    """Tell the other user an event was removed."""
    recipient: User | None = _other_user(deleted_by.id)
    if recipient is None:
        return

    subject: str = f"Event removed: {event_title}"
    message: str = f'{deleted_by.username} removed the calendar event "{event_title}".'

    notify(recipient, subject, message, notif_type="event")
