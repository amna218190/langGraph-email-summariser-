import datetime
import json
import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_FILE = "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def save_tokens_to_json(creds: Credentials):
    """Saves the access token, refresh token, expiry, and timestamp to token.json."""
    token_payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
        "saved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    with open(TOKEN_FILE, "w") as token_file:
        json.dump(token_payload, token_file, indent=4)
    print(f"[AUTH SUCCESS] Credentials saved successfully to '{TOKEN_FILE}'.")


def get_gmail_credentials() -> Credentials:
    """Authenticates with Gmail via OAuth 2.0 and manages token storage."""
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env file."
        )

    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    # 2. Check if the loaded token is valid or needs refreshing
    if creds and creds.valid:
        print("[AUTH] Valid token found in token.json.")
        return creds

    if creds and creds.expired and creds.refresh_token:
        print("[AUTH] Access token expired. Refreshing using refresh token...")
        creds.refresh(Request())
        save_tokens_to_json(creds)
        return creds

    # 3. First-time Authentication: Launch browser to prompt for username & password
    print(
        "[AUTH] No valid token found. Opening browser for Gmail login/consent..."
    )

    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save newly generated access & refresh tokens
    save_tokens_to_json(creds)
    return creds


if __name__ == "__main__":
    credentials = get_gmail_credentials()
    print("[AUTH DONE] Connection with Gmail established.")