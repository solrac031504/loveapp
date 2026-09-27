import os


class NotificationConfig:
    """Settings for outgoing notifications.

    Email is sent through a Gmail account using SMTP. Set these in the
    app's `.env` file (see `loveapp/app.py`, which loads it):

        GMAIL_ADDRESS=you@gmail.com
        GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

    `GMAIL_APP_PASSWORD` is a Gmail *app password*, not the account's
    regular login password -- generate one at
    https://myaccount.google.com/apppasswords (requires 2-Step
    Verification to be enabled on the account).

    Texting isn't wired up to a real provider yet. Text notifications
    are only logged to the console for now.
    """

    GMAIL_ADDRESS: str | None = os.getenv("GMAIL_ADDRESS")
    GMAIL_APP_PASSWORD: str | None = os.getenv("GMAIL_APP_PASSWORD")
    GMAIL_SMTP_HOST: str = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
    GMAIL_SMTP_PORT: int = int(os.getenv("GMAIL_SMTP_PORT", "465"))

    @classmethod
    def email_enabled(cls) -> bool:
        """Whether enough Gmail config is present to actually send mail."""
        return bool(cls.GMAIL_ADDRESS and cls.GMAIL_APP_PASSWORD)
