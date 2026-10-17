"""Low-level notification delivery.

Two channels: email (via Gmail API) and text (not wired
up to a real provider yet, so it's just logged to the console). Both
channels record what they sent in the corresponding *Notification table
regardless of whether delivery actually succeeded, and both respect the
recipient's own `send_email` / `send_message` preference flags on
`User`.

Higher-level "when X happens, notify Y" logic lives in
`complaint_notifications.py`; this module only knows how to deliver a
message once the caller has already decided who should get it.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

try:
    from ..config import NotificationConfig
    from ..extensions import db
    from ..models import EmailNotification, TextNotification, User
except ImportError:
    from config import NotificationConfig
    from extensions import db
    from models import EmailNotification, TextNotification, User


# TODO switch message to template name with added context
def notify(user: User, subject: str, message: str, notif_type: str) -> None:
    """Send `message` to `user` over every channel they have enabled.

    Never raises: a delivery failure (e.g. bad Gmail credentials, no
    network) is logged to the console but must not take down whatever
    request triggered the notification, such as filing a complaint.
    """
    if user.send_email:
        _send_email(user, subject, message, notif_type)
    if user.send_message:
        _send_text(user, message, notif_type)


def _send_email(user: User, subject: str, message: str, notif_type: str) -> None:
    email_notification = EmailNotification(
        recipient_id=user.id,
        subject=subject,
        message=message,
        notif_type=notif_type,
    )

    db.session.add(email_notification)
    db.session.commit()

    if not NotificationConfig.email_enabled():
        print(
            f"[email:not configured] would email {user.email!r}: "
            f"{subject!r} -- {message!r}"
        )
        return

    try:
        message_id = _deliver_email(user.email, subject, message)
        email_notification.message_id = message_id
        db.session.commit()

    except Exception as ex:  # noqa: BLE001 -- delivery failures must not bubble up
        print(f"[email:error] failed to email {user.email!r}: {ex}")


def _get_credentials(token_path: str, scopes: list[str]) -> Credentials:
    """
    Get credentials from token file or refresh token
    """
    creds: Credentials = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds.valid:
        if creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            print(
                "[email:error] token invalid and no refresh token. Reauthorization needed"
            )

    return creds


def _deliver_email(to_address: str, subject: str, body: str) -> str:
    # Only called when NotificationConfig.email_enabled() is true, which
    # guarantees both of these are non-None -- asserted here for pyright.
    GMAIL_CREDS_PATH: str | None = NotificationConfig.GMAIL_CREDS_PATH
    GMAIL_TOKEN_PATH: str | None = NotificationConfig.GMAIL_TOKEN_PATH
    SCOPES: list[str] = NotificationConfig.SCOPES
    assert GMAIL_CREDS_PATH and GMAIL_TOKEN_PATH

    service = build(
        "gmail", "v1", credentials=_get_credentials(GMAIL_TOKEN_PATH, SCOPES)
    )

    msg = EmailMessage()
    msg.set_content(body)
    msg["To"] = to_address
    msg["Subject"] = subject

    encoded: str = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    result = (
        service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    )

    return result["id"]


def _send_text(user: User, message: str, notif_type: str) -> None:
    db.session.add(
        TextNotification(recipient_id=user.id, message=message, notif_type=notif_type)
    )
    db.session.commit()

    # No SMS provider hooked up yet -- console log stands in for it.
    print(f"[text] to {user.phone}: {message}")
