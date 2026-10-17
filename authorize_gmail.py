"""Run this ONCE on your own computer (not in Colab) to create token.json.

Requires credentials.json (OAuth client ID of type "Desktop app") in the same folder.
    pip install google-auth-oauthlib google-api-python-client
"""

from google.auth.external_account_authorized_user import Credentials as UserCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES: list[str] = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> None:
    flow: InstalledAppFlow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
    )
    # access_type/prompt make sure Google returns a long-lived refresh token
    creds: UserCredentials | Credentials = flow.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )
    with open("token.json", "w") as f:
        f.write(creds.to_json())
    print("Saved token.json")


if __name__ == "__main__":
    main()
