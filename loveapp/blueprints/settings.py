from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.wrappers.response import Response

try:
    from ..extensions import db
    from ..forms import (
        ChangePasswordForm,
        ContactInfoForm,
        NotificationPreferencesForm,
    )
except ImportError:
    from extensions import db
    from forms import (
        ChangePasswordForm,
        ContactInfoForm,
        NotificationPreferencesForm,
    )

settings = Blueprint("settings", __name__)

# Each section of the page is its own form. They all post to the same URL, and
# a per-form prefix keeps their field names/ids from colliding and lets us tell
# which one was submitted.
PREFS_PREFIX = "prefs"
CONTACT_PREFIX = "contact"
PASSWORD_PREFIX = "password"


@settings.route("/settings", methods=["GET", "POST"])
@login_required
def index() -> Response | str:
    is_post: bool = request.method == "POST"

    def submitted(prefix: str) -> bool:
        return is_post and f"{prefix}-submit" in request.form

    # Only bind request data to the form that was actually submitted, so the
    # other sections keep showing the user's saved values rather than blanks.
    prefs_form = NotificationPreferencesForm(
        prefix=PREFS_PREFIX,
        obj=current_user,
        formdata=request.form if submitted(PREFS_PREFIX) else None,
    )
    contact_form = ContactInfoForm(
        current_user.id,
        prefix=CONTACT_PREFIX,
        obj=current_user,
        formdata=request.form if submitted(CONTACT_PREFIX) else None,
    )
    password_form = ChangePasswordForm(
        prefix=PASSWORD_PREFIX,
        formdata=request.form if submitted(PASSWORD_PREFIX) else None,
    )

    if submitted(PREFS_PREFIX) and prefs_form.validate():
        current_user.send_email = bool(prefs_form.send_email.data)
        current_user.send_message = bool(prefs_form.send_message.data)
        db.session.commit()
        flash("Notification preferences saved", "success")
        return redirect(url_for("settings.index"))

    if submitted(CONTACT_PREFIX) and contact_form.validate():
        current_user.email = (contact_form.email.data or "").strip()
        current_user.phone = (contact_form.phone.data or "").strip()
        db.session.commit()
        flash("Contact info updated", "success")
        return redirect(url_for("settings.index"))

    if submitted(PASSWORD_PREFIX) and password_form.validate():
        if not current_user.check_password(password_form.current_password.data):
            password_form.current_password.errors.append(  # type: ignore
                "Current password is incorrect."
            )
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Password changed", "success")
            return redirect(url_for("settings.index"))

    return render_template(
        "settings.html",
        prefs_form=prefs_form,
        contact_form=contact_form,
        password_form=password_form,
    )
