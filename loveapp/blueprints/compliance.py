from flask import Blueprint, render_template

compliance = Blueprint(
    "compliance", __name__, template_folder="../templates/compliance"
)


@compliance.route("/privacy")
def privacy() -> str:
    return render_template("compliance/privacy.html")


@compliance.route("/terms")
def terms() -> str:
    return render_template("compliance/terms.html")
