from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


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
