"""Notification triggers for complaint events.

LoveApp is built for exactly one couple (see `create-user` in app.py --
there's no self-service signup), so "the other user" is simply whichever
User row isn't the one in question.
"""

from __future__ import annotations

try:
    from ..models import Complaint, User
    from .notifier import notify
except ImportError:
    from models import Complaint, User
    from services.notifier import notify


def _other_user(user_id: int) -> User | None:
    return User.query.filter(User.id != user_id).first()


def notify_complaint_filed(complaint: Complaint) -> None:
    """Tell the other user a new complaint has been filed against them."""
    recipient: User | None = _other_user(complaint.submitter_id)
    if recipient is None:
        return

    submitter_name: str = (
        complaint.submitter.username if complaint.submitter else "Someone"
    )
    subject: str = f"New complaint: {complaint.title}"
    message: str = f'{submitter_name} filed a new complaint: "{complaint.title}"\n\n{complaint.body}'
    notify(recipient, subject, message, notif_type="complaint")


def notify_status_changed(
    complaint: Complaint, old_status: str, new_status: str, changed_by: User
) -> None:
    """Tell the submitter their complaint's status changed.

    Skipped if the submitter is the one who made the change -- they
    don't need to be told about their own action.
    """
    if changed_by.id == complaint.submitter_id:
        return

    submitter: User = complaint.submitter
    if submitter is None:
        return

    subject: str = f'"{complaint.title}" is now {new_status}'
    message: str = (
        f'Your complaint "{complaint.title}" was updated from '
        f"{old_status} to {new_status} by {changed_by.username}."
    )
    notify(submitter, subject, message, notif_type="complaint")
