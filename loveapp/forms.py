from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    EmailField,
    IntegerField,
    PasswordField,
    StringField,
    SubmitField,
    TelField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

MIN_PASSWORD_LENGTH = 8


class LoginForm(FlaskForm):
    """Login form. There is no registration form -- users are inserted
    manually into the User table (see the `flask create-user` CLI command
    registered in app.py)."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Log In")


class ComplaintForm(FlaskForm):
    """Form for filing a new complaint. `status` and `created_at` are set
    server-side (status is always "open" for a new complaint; created_at
    defaults to the current UTC time), so they aren't fields here."""

    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    body = TextAreaField("Description", validators=[DataRequired()])
    mood = TextAreaField("Mood", validators=[Optional()])
    severity_level = IntegerField(
        "Severity (1-10)",
        validators=[Optional(), NumberRange(min=1, max=10)],
    )
    submit = SubmitField("Add Complaint")


class CalendarEventForm(FlaskForm):
    """Form for creating and editing a calendar event.

    `event_type` is a free-text field rather than a select: the couple can
    invent new event types on the fly, and the blueprint looks up (or
    creates) the matching `CalendarEventType` row by name. Leaving it
    blank is fine -- the event just won't have a type.
    """

    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    description = TextAreaField("Description", validators=[Optional()])
    event_type = StringField("Event type", validators=[Optional(), Length(max=100)])
    is_all_day = BooleanField("All day")
    start_time = DateTimeLocalField(
        "Start", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_time = DateTimeLocalField(
        "End", format="%Y-%m-%dT%H:%M", validators=[Optional()]
    )
    submit = SubmitField("Save Event")

    def validate_end_time(self, field: DateTimeLocalField) -> None:
        if field.data and self.start_time.data and field.data < self.start_time.data:
            raise ValidationError("End time must be after the start time.")


class NotificationPreferencesForm(FlaskForm):
    """Which channels the user wants to be contacted on."""

    send_email = BooleanField("Email notifications")
    send_message = BooleanField("Text message notifications")
    submit = SubmitField("Save Preferences")


class ContactInfoForm(FlaskForm):
    """Edit the user's email address and phone number.

    Both columns are unique on `User`, so the form takes the id of the user
    being edited and rejects values that already belong to someone else.
    """

    email = EmailField(
        "Email",
        validators=[
            DataRequired(),
            Length(max=120),
            Regexp(
                r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="Enter a valid email address."
            ),
        ],
    )
    phone = TelField(
        "Phone number",
        validators=[
            DataRequired(),
            Length(max=20),
            Regexp(r"^\+?[\d\s().-]+$", message="Enter a valid phone number."),
        ],
    )
    submit = SubmitField("Save Contact Info")

    def __init__(self, user_id: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._user_id: int = user_id

    def validate_email(self, field: EmailField) -> None:
        # Imported lazily to match the dual package/script import style used
        # elsewhere in the app.
        try:
            from .models import User
        except ImportError:
            from models import User

        existing = User.query.filter(
            User.email == field.data.strip(),  # type: ignore
            User.id != self._user_id,
        ).first()
        if existing:
            raise ValidationError("That email is already in use.")

    def validate_phone(self, field: TelField) -> None:
        try:
            from .models import User
        except ImportError:
            from models import User

        digits: str = "".join(ch for ch in (field.data or "") if ch.isdigit())
        if len(digits) < 7:
            raise ValidationError("Enter a valid phone number.")

        existing = User.query.filter(
            User.phone == (field.data or "").strip(),  # type: ignore
            User.id != self._user_id,
        ).first()
        if existing:
            raise ValidationError("That phone number is already in use.")


class ChangePasswordForm(FlaskForm):
    """Change password. The current password is required so that someone
    with access to an unlocked, logged-in session can't silently lock the
    real owner out."""

    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(),
            Length(
                min=MIN_PASSWORD_LENGTH,
                message=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            ),
        ],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Change Password")
