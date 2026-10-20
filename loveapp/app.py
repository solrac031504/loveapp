import os
import secrets

import click
from dotenv import load_dotenv
from flask import Flask, Response, render_template
from flask_login import login_required
from flask_migrate import Migrate
from google_auth_oauthlib.flow import Flow

if __package__:
    from . import models
    from .blueprints.auth import auth as auth_blueprint
    from .blueprints.calendar import calendar as calendar_blueprint
    from .blueprints.complaints import complaints as complaints_blueprint
    from .blueprints.compliance import compliance as compliance_blueprint
    from .blueprints.settings import settings as settings_blueprint
    from .extensions import csrf, db, login_manager
    from .models import User
else:
    import models  # noqa: F401
    from blueprints.auth import auth as auth_blueprint
    from blueprints.calendar import calendar as calendar_blueprint
    from blueprints.complaints import complaints as complaints_blueprint
    from blueprints.compliance import compliance as compliance_blueprint
    from blueprints.settings import settings as settings_blueprint
    from extensions import csrf, db, login_manager
    from models import User


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    # Load .env from the app directory so the database URI is stable
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    # Use the configured secret or a generated fallback.
    secret_key: str = os.getenv("SECRET_KEY") or secrets.token_hex()
    default_db_path: str = os.path.join(app.instance_path, "LoveApp.db")
    sqlalchemy_database_uri: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI", f"sqlite:///{default_db_path}"
    )
    if sqlalchemy_database_uri.startswith("sqlite:///"):
        sqlite_path: str = sqlalchemy_database_uri.replace("sqlite:///", "", 1)
        if not os.path.isabs(sqlite_path):
            sqlite_path: str = os.path.abspath(
                os.path.join(os.path.dirname(__file__), sqlite_path)
            )
            sqlalchemy_database_uri = f"sqlite:///{sqlite_path}"

    app.config["SECRET_KEY"] = secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = sqlalchemy_database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    Migrate(app, db)

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(calendar_blueprint)
    app.register_blueprint(complaints_blueprint)
    app.register_blueprint(settings_blueprint)
    app.register_blueprint(compliance_blueprint)

    @app.route("/")
    @login_required
    def home() -> str:
        return render_template("home.html")

    @app.route("/favicon.ico")
    def favicon() -> Response:
        return app.send_static_file("favicon.ico")

    # Create all tables on first run
    with app.app_context():
        db.create_all()

    register_cli(app)
    password_change_cli(app)
    authorize_gmail_cli(app)

    return app


def register_cli(app: Flask) -> None:
    """CLI commands for managing users, since there is no self-service
    registration flow -- users are inserted manually into the User table."""

    @app.cli.command("create-user")
    @click.argument("username")
    @click.argument("email")
    @click.argument("phone")
    @click.password_option()
    def create_user(username: str, email: str, phone: str, password: str) -> None:
        """Create a new user. Example:

        flask create-user carlos carlos@example.com 555-0100
        """
        if User.query.filter_by(username=username).first():
            click.echo(f"Error: username '{username}' already exists.")
            return

        user = User(username=username, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created user '{username}' (id={user.id}).")


def password_change_cli(app: Flask) -> None:
    """CLI commands for updating a user's password in case password is forgotten"""

    @app.cli.command("reset-password")
    @click.argument("username")
    @click.password_option()
    def reset_password(username: str, password: str) -> None:
        """Update a password"""
        user: User | None = User.query.filter_by(username=username).first()

        if not user:
            click.echo(f"Error: user '{username}' does not exist")
            return

        user.set_password(password)
        db.session.commit()
        click.echo(f"Updated '{username}' password")


def authorize_gmail_cli(app: Flask) -> None:
    """CLI to generate Gmail token file on a headless server.

    Uses a manual copy/paste flow with a Web application OAuth client, so no
    browser is needed on the server.

    Requires GMAIL_REDIRECT_URI (optional, defaults to http://localhost:8080/)
    to be registered under "Authorized redirect URIs" for the OAuth client in
    Google Cloud Console.
    """

    @app.cli.command("authorize-gmail")
    def authorize_gmail() -> None:
        GMAIL_CREDS_PATH: str | None = os.getenv("GMAIL_CREDS_PATH")
        GMAIL_TOKEN_PATH: str | None = os.getenv("GMAIL_TOKEN_PATH")
        SCOPES: str | None = os.getenv("GMAIL_SCOPES")
        redirect_uri: str = os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8080/")

        if not (GMAIL_CREDS_PATH and GMAIL_TOKEN_PATH and SCOPES):
            click.echo("Creds path or token path is not specified")
            return

        scopes: list[str] = SCOPES.split(";")

        # oauthlib refuses http:// redirects by default; the redirect to
        # localhost is never actually served, we only copy the URL from it.
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        # Don't fail if Google returns the scopes in a different order/form.
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

        flow: Flow = Flow.from_client_secrets_file(
            GMAIL_CREDS_PATH, scopes=scopes, redirect_uri=redirect_uri
        )

        # access_type/prompt make sure Google returns a long-lived refresh token
        auth_url, _state = flow.authorization_url(
            access_type="offline", prompt="consent"
        )

        click.echo("\n1. Open this URL in a browser on your own computer:\n")
        click.echo(auth_url)
        click.echo(
            "\n2. Sign in and approve access. The browser will then fail to load"
            f"\n   {redirect_uri} -- that is expected."
            "\n3. Copy the FULL URL from the browser's address bar"
            "\n   (it contains ?code=...) and paste it below.\n"
        )
        response_url: str = click.prompt("Paste the redirected URL").strip()

        flow.fetch_token(authorization_response=response_url)

        with open(GMAIL_TOKEN_PATH, "w") as f:
            f.write(flow.credentials.to_json())
        click.echo("Saved token file")


if __name__ == "__main__":
    create_app().run(debug=True)
