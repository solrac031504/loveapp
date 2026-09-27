from datetime import datetime, timezone
from typing import Any

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, relationship
from werkzeug.security import check_password_hash, generate_password_hash

if __package__:
    from .extensions import db
else:
    from extensions import db


class User(UserMixin, db.Model):
    """Represents a single user login"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    login_count = db.Column(db.Integer, default=0, nullable=False)
    last_login_utc = db.Column(db.DateTime, nullable=True)
    send_email = db.Column(db.Boolean, default=True, nullable=False)
    send_message = db.Column(db.Boolean, default=True, nullable=False)

    def __init__(self, username: str, email: str, phone: str) -> None:
        self.username: str = username
        self.email: str = email
        self.phone: str = phone

    def set_password(self, password: str) -> None:
        """Hash and store a password. Use this when manually creating users."""
        self.password_hash: str = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class CalendarEventType(db.Model):
    """Represents a calendar event type"""

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100))


class CalendarEvent(db.Model):
    """Represents a calendar event"""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_type_id = db.Column(db.Integer, db.ForeignKey("calendar_event_type.id"))
    is_all_day = db.Column(db.Boolean)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class EmailNotification(db.Model):
    """Tracks notifications sent via email"""

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notif_type = db.Column(db.String(50))  # 'event', 'complaint', 'system'

    def __init__(
        self, recipient_id: int, subject: str, message: str, notif_type: str
    ) -> None:
        self.recipient_id: int = recipient_id
        self.subject: str = subject
        self.message: str = message
        self.notif_type: str = notif_type


class TextNotification(db.Model):
    """Tracks notifications sent via text"""

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notif_type = db.Column(db.String(50))  # 'event', 'complaint', 'system'

    def __init__(self, recipient_id: int, message: str, notif_type: str) -> None:
        self.recipient_id: int = recipient_id
        self.message: str = message
        self.notif_type: str = notif_type


class Complaint(db.Model):
    """Represents a compliant filed from a user"""

    id = db.Column(db.Integer, primary_key=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(50))  # 'frustrated', 'sad', 'upset'
    status = db.Column(db.String(50), default="open")  # open, acknowledged, resolved
    severity_level = db.Column(db.Integer)  # 1-10
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    submitter: Mapped["User"] = relationship(
        "User", foreign_keys=[submitter_id], backref="complaints_filed"
    )

    def __init__(
        self,
        submitter_id: int,
        title: str,
        body: str,
        mood: str | None,
        severity_level: int,
        status: str,
    ) -> None:
        self.submitter_id: Any = submitter_id
        self.title: Any = title
        self.body: Any = body
        self.mood: Any = mood
        self.severity_level: Any = severity_level
        self.status: Any = status
