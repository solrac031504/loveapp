# LoveApp

LoveApp is a Flask-based web application for managing relationship communication, complaint tracking, and notifications between two users. The app includes a private login flow, complaint filing and status updates, and support for email/text-style notifications for important events.

## Features

- Secure user authentication with Flask-Login
- Complaint submission and status tracking
- Open/resolved complaint filtering
- Email and SMS-style notification support
- Calendar event model support for future scheduling features
- SQLite database with Flask-SQLAlchemy and Flask-Migrate
- CLI command for creating users manually

## Project Structure

- `loveapp/app.py` — application factory and CLI registration
- `loveapp/models.py` — database models for users, complaints, notifications, and calendar data
- `loveapp/blueprints/` — Flask blueprints for authentication and complaints
- `loveapp/services/` — notification logic
- `loveapp/templates/` — HTML templates
- `loveapp/static/` — frontend assets
- `loveapp/migrations/` — Alembic migration files

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- SQLite
- APScheduler
- Flask-Migrate

## Prerequisites

- Python 3.10+
- A virtual environment tool such as `venv`

## Setup

From the repository root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r loveapp/requirements.txt
```

Create a `.env` file inside the `loveapp` directory for local configuration if needed. Example:

```env
SECRET_KEY=change-me
SQLALCHEMY_DATABASE_URI=sqlite:////absolute/path/to/LoveApp.db
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

Notes:

- `SECRET_KEY` is required for secure session cookies.
- The app will fall back to a local SQLite database in `loveapp/instance/LoveApp.db` if no database URI is configured.
- Gmail settings are optional and only needed if you want real email notifications enabled.

## Running the App

From the repository root:

```bash
export FLASK_APP=loveapp.app
flask run --debug
```

Or run the app module directly:

```bash
python loveapp/app.py
```

The app will start on the default Flask development server, typically at:

```text
http://127.0.0.1:5000/
```

## Creating a User

This app does not include a public registration screen. Users are created through the Flask CLI:

```bash
flask create-user <username> <email> <phone> --password <password>
```

Example:

```bash
flask create-user someuser someuser@example.com 555-0100 --password password
```

The command will prompt for a password and store the hashed password in the database.

## Database Notes

On first app startup, the database tables are created automatically in the app context. For migrations and schema changes, the project includes Alembic support under `loveapp/migrations`.