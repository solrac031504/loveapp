import os
import secrets

import click
from dotenv import load_dotenv
from flask import Flask, Response, render_template
from flask_login import login_required

if __package__:
    from . import models
    from .blueprints.auth import auth as auth_blueprint
    from .extensions import db, login_manager
    from .models import User
else:
    import models  # noqa: F401
    from blueprints.auth import auth as auth_blueprint
    from extensions import db, login_manager
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

    # Register blueprints
    app.register_blueprint(auth_blueprint)

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


if __name__ == "__main__":
    create_app().run(debug=True)
