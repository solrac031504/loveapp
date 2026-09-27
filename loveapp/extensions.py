from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

login_manager = LoginManager()
# Ignore a weird outdated stub issue
login_manager.login_view = "auth.login"  # type: ignore[assignment]
login_manager.login_message = "Please log in to access this page"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    if __package__:
        from .models import User
    else:
        from models import User

    return User.query.get(int(user_id))
