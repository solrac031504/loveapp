from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_sqlalchemy.query import Query
from werkzeug.wrappers.response import Response

try:
    from ..extensions import db
    from ..forms import ComplaintForm
    from ..models import Complaint
except ImportError:
    from extensions import db
    from forms import ComplaintForm
    from models import Complaint

complaints = Blueprint("complaints", __name__)

# Valid values stored in Complaint.status
STATUSES = ("open", "acknowledged", "resolved")

# Extra filter option meaning "anything that isn't resolved yet" -- this is
# the default view for the "open complaints" tab.
DEFAULT_STATUS_FILTER = "unresolved"


def _complaints_context(status_filter: str) -> dict:
    """Shared query logic for the complaints page.

    - "Open complaints": complaints filed against the current user, i.e.
      filed by the other person. LoveApp is built for a single couple (see
      the `create-user` CLI command -- there's no self-service signup), so
      "against the current user" just means "filed by anyone other than
      the current user". Filterable by status, sorted newest first.
    - "My complaint history": every complaint the current user has filed
      themselves, regardless of status, sorted newest first.
    """
    if status_filter != DEFAULT_STATUS_FILTER and status_filter not in STATUSES:
        status_filter = DEFAULT_STATUS_FILTER

    open_complaints_query: Query = Complaint.query.filter(
        Complaint.submitter_id != current_user.id
    )
    if status_filter == DEFAULT_STATUS_FILTER:
        open_complaints_query: Query = open_complaints_query.filter(
            Complaint.status != "resolved"
        )
    else:
        open_complaints_query: Query = open_complaints_query.filter_by(
            status=status_filter
        )

    open_complaints = open_complaints_query.order_by(Complaint.created_at.desc()).all()

    my_complaint_history = (
        Complaint.query.filter_by(submitter_id=current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    return {
        "open_complaints": open_complaints,
        "my_complaint_history": my_complaint_history,
        "status_filter": status_filter,
        "statuses": STATUSES,
    }


@complaints.route("/complaints")
@login_required
def index() -> str:
    status_filter: str = (
        request.args.get("status", DEFAULT_STATUS_FILTER).strip().lower()
    )
    context = _complaints_context(status_filter)
    context["form"] = ComplaintForm()
    return render_template("complaints.html", **context)


@complaints.route("/complaints/new", methods=["POST"])
@login_required
def new() -> Response | tuple[str, int]:
    """Create a new complaint filed by the current user. Status is always
    "open" and created_at is left to the model default (current UTC time
    at insert), regardless of what the client sends."""

    form = ComplaintForm()
    if form.validate_on_submit():
        # Added coalesces to appease compiler
        complaint = Complaint(
            submitter_id=current_user.id,
            title=form.title.data or "",
            body=form.body.data or "",
            mood=form.mood.data or None,
            severity_level=form.severity_level.data or 1,
            status="open",
        )
        db.session.add(complaint)
        db.session.commit()
        flash("Complaint added", "info")
        return redirect(url_for("complaints.index"))

    # Validation failed: re-render the page with the entered data and
    # errors preserved, and the modal reopened, instead of silently
    # discarding what the user typed via a redirect.
    status_filter: str = (
        request.args.get("status", DEFAULT_STATUS_FILTER).strip().lower()
    )
    context = _complaints_context(status_filter)
    context["form"] = form
    context["open_modal"] = True
    return render_template("complaints.html", **context), 400


@complaints.route("/complaints/<int:complaint_id>/status", methods=["POST"])
@login_required
def update_status(complaint_id: int) -> Response:
    """Update a complaint's status. Both users can update the status of
    ANY complaint, including their own -- there's no ownership check here.
    Only deletion (below) is restricted to the original submitter."""

    complaint = Complaint.query.get_or_404(complaint_id)

    new_status: str = request.form.get("status", "").strip().lower()
    if new_status not in STATUSES:
        flash("Invalid status", "danger")
        return redirect(url_for("complaints.index"))

    if new_status != complaint.status:
        complaint.status = new_status
        complaint.resolved_at = (
            datetime.now(timezone.utc) if new_status == "resolved" else None
        )
        db.session.commit()
        flash(f'"{complaint.title}" marked as {new_status}.', "info")

    return redirect(url_for("complaints.index"))


@complaints.route("/complaints/<int:complaint_id>/delete", methods=["POST"])
@login_required
def delete(complaint_id: int) -> Response:
    """Hard-delete a complaint. Unlike status updates, this is restricted
    to the user who originally filed the complaint."""

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.submitter_id != current_user.id:
        abort(403)

    db.session.delete(complaint)
    db.session.commit()

    flash("Complaint deleted", "info")
    return redirect(url_for("complaints.index"))
