from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    IntegerField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


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
