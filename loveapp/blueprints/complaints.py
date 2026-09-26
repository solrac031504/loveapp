from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from flask_sqlalchemy.query import Query

try:
    from ..models import Complaint
except ImportError:
    from models import Complaint

complaints = Blueprint("complaints", __name__)

# Valid values stored in Complaint.status
STATUSES = ("open", "acknowledged", "resolved")

# Extra filter option meaning "anything that isn't resolved yet" -- this is
# the default view for the "open complaints" tab.
DEFAULT_STATUS_FILTER = "unresolved"


@complaints.route("/complaints")
@login_required
def index() -> str:
    """Complaints page with two tabs:

    - "Open complaints": complaints filed against the current user, i.e.
      filed by the other person. LoveApp is built for a single couple (see
      the `create-user` CLI command -- there's no self-service signup), so
      "against the current user" just means "filed by anyone other than
      the current user". Filterable by status, sorted newest first.
    - "My complaint history": every complaint the current user has filed
      themselves, regardless of status, sorted newest first.
    """

    status_filter: str = (
        request.args.get("status", DEFAULT_STATUS_FILTER).strip().lower()
    )
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

    return render_template(
        "complaints.html",
        open_complaints=open_complaints,
        my_complaint_history=my_complaint_history,
        status_filter=status_filter,
        statuses=STATUSES,
    )
