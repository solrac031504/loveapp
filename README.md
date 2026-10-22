# LoveApp

LoveApp is a private Flask application for two people to share a calendar and
manage relationship complaints. Users sign in with accounts created by an
administrator; there is no public registration page.

## Features

- Login-protected home, calendar, complaints, and account settings
- Shared calendar with event types, event editing, and creator-only deletion
- Complaint filing, status changes (`open`, `acknowledged`, and `resolved`),
  and submitter-only deletion
- Per-user email and text notification preferences
- Optional email delivery through the Gmail API
- Privacy and terms pages at `/privacy` and `/terms`
- SQLite database, SQLAlchemy models, and Flask-Migrate/Alembic migrations

The app is designed for two accounts, not as a multi-couple service. Email
notifications are sent through Gmail only when Gmail OAuth is configured.
There is no SMS provider connected: text notifications are stored in the
database and written to the application log.

## Project layout

```text
deploy/                     Example Nginx, systemd, and update configuration
loveapp/
  app.py                    Application factory and Flask CLI commands
  blueprints/               Authentication, calendar, complaints, settings,
                            and compliance routes
  services/                 Calendar and complaint notification behavior
  templates/                Jinja templates
  static/                   CSS and image assets
  migrations/               Alembic migration environment and revisions
  requirements.txt          Pinned Python dependencies
```

## Requirements

- Python 3.10 or newer
- `pip` and Python's `venv` module

## Local setup

Run these commands from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r loveapp/requirements.txt
```

Create `loveapp/.env` for local application configuration:

```env
SECRET_KEY=replace-with-a-long-random-value
SQLALCHEMY_DATABASE_URI=sqlite:///LoveApp.db
```

The app loads this file when its application factory runs. If
`SQLALCHEMY_DATABASE_URI` is omitted, the database defaults to
`loveapp/instance/LoveApp.db`. Relative SQLite paths are resolved from the
`loveapp` directory. Keep secrets and OAuth credential files out of source
control.

Start the development server from the repository root:

```bash
flask --app loveapp.app run --debug
```

Open <http://127.0.0.1:5000/>. The home page and application features require
sign-in.

## Accounts

There is no self-service sign-up. Create accounts from the repository root
with the Flask CLI; it prompts for a password if one is not supplied:

```bash
flask --app loveapp.app create-user <username> <email> <phone>
```

For example:

```bash
flask --app loveapp.app create-user alex alex@example.com 555-0100
```

Passwords are stored as password hashes. To set a new password for an
existing account:

```bash
flask --app loveapp.app reset-password <username>
```

## Database and migrations

The application creates any missing database tables during startup. The
project also includes Flask-Migrate/Alembic revisions under
`loveapp/migrations/`. To apply available migrations:

```bash
flask --app loveapp.app db upgrade
```

When changing the models, generate and apply a migration:

```bash
flask --app loveapp.app db migrate -m "describe the schema change"
flask --app loveapp.app db upgrade
```

Review generated migration files before applying or committing them.

## Optional Gmail notifications

To send email notifications, configure a Gmail API OAuth client and set these
environment variables in the environment that starts Flask:

| Variable | Purpose |
| --- | --- |
| `GMAIL_CREDS_PATH` | Path to the Google OAuth client credentials JSON file |
| `GMAIL_TOKEN_PATH` | Path where the authorized token JSON will be saved/read |
| `GMAIL_SCOPES` | Gmail OAuth scopes, separated by semicolons |
| `GMAIL_REDIRECT_URI` | Optional OAuth redirect URI; defaults to `http://localhost:8080/` |
| `BASE_URL` | Public base URL used to build links in notification messages |

For example, the send-mail scope is
`https://www.googleapis.com/auth/gmail.send`. Register the redirect URI in the
Google Cloud OAuth client configuration. With the variables set, authorize
the account from the repository root:

```bash
flask --app loveapp.app authorize-gmail
```

The command prints an authorization URL. Open it in a browser, approve access,
then paste the complete redirected URL when prompted. The redirect page itself
does not need to load successfully; the command reads the authorization code
from its URL.

Email notifications are recorded even when Gmail delivery is not configured;
in that case the app logs that it would have sent the message. Each account
can enable or disable email and text notifications in **Settings**. Text
notifications currently only create a database record and log the message.

For locally configured Gmail variables and `BASE_URL`, export them before
starting Flask so they are present when the notification modules load.

## Deployment files

The `deploy/` directory contains examples for the current Linux deployment:

- `loveapp.service` runs Gunicorn on `127.0.0.1:8000` with one worker and four
  threads.
- `loveapp.nginx.conf` proxies HTTP traffic to Gunicorn. HTTPS can be added
  with Certbot as noted in the configuration.
- `update.sh` pulls the latest code, installs requirements and Gunicorn, then
  restarts the `loveapp` systemd service.

These files assume the paths and service account shown in the files
(`/srv/loveapp/...`, `deploy`) and the configured host name; adjust them for
your server before installing. The update script expects a working Git
checkout and `sudo` permission to restart the service.
