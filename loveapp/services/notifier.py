"""Low-level notification delivery.

Two channels: email (sent for real, via Gmail SMTP) and text (not wired
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

import smtplib
import ssl
from email.message import EmailMessage

try:
    from ..config import NotificationConfig
    from ..extensions import db
    from ..models import EmailNotification, TextNotification, User
except ImportError:
    from config import NotificationConfig
    from extensions import db
    from models import EmailNotification, TextNotification, User


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
    db.session.add(
        EmailNotification(
            recipient_id=user.id,
            subject=subject,
            message=message,
            notif_type=notif_type,
        )
    )
    db.session.commit()

    if not NotificationConfig.email_enabled():
        print(
            f"[email:not configured] would email {user.email!r}: "
            f"{subject!r} -- {message!r}"
        )
        return

    try:
        _deliver_email(user.email, subject, message)
    except Exception as ex:  # noqa: BLE001 -- delivery failures must not bubble up
        print(f"[email:error] failed to email {user.email!r}: {ex}")


def _deliver_email(to_address: str, subject: str, body: str) -> None:
    # Only called when NotificationConfig.email_enabled() is true, which
    # guarantees both of these are non-None -- asserted here for pyright.
    gmail_address: str | None = NotificationConfig.GMAIL_ADDRESS
    gmail_app_password: str | None = NotificationConfig.GMAIL_APP_PASSWORD
    assert gmail_address and gmail_app_password

    msg: EmailMessage = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address
    msg.set_content(body)

    context: ssl.SSLContext = ssl.create_default_context()
    server: smtplib.SMTP_SSL
    with smtplib.SMTP_SSL(
        NotificationConfig.GMAIL_SMTP_HOST,
        NotificationConfig.GMAIL_SMTP_PORT,
        context=context,
    ) as server:
        server.login(gmail_address, gmail_app_password)
        server.send_message(msg)


def _send_text(user: User, message: str, notif_type: str) -> None:
    db.session.add(
        TextNotification(recipient_id=user.id, message=message, notif_type=notif_type)
    )
    db.session.commit()

    # No SMS provider hooked up yet -- console log stands in for it.
    print(f"[text] to {user.phone}: {message}")
