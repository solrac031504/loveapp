import os


class NotificationConfig:
    """Settings for outgoing notifications.

    Email is sent through Gmail's API as the authenticated account

    Texting isn't wired up to a real provider yet. Text notifications
    are only logged to the console for now.
    """

    GMAIL_CREDS_PATH: str | None = os.getenv("GMAIL_CREDS_PATH")
    GMAIL_TOKEN_PATH: str | None = os.getenv("GMAIL_TOKEN_PATH")

    @classmethod
    def email_enabled(cls) -> bool:
        """Whether enough Gmail config is present to actually send mail."""
        return bool(cls.GMAIL_CREDS_PATH and cls.GMAIL_TOKEN_PATH)
