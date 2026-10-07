import base64
import datetime
import json
import os
import re
import time
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from html import unescape
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from agent import run_agent

from oauth_handler import save_tokens_to_json, TOKEN_FILE, SCOPES


def ensure_valid_token_with_expiry_check() -> Credentials:
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(
            f"'{TOKEN_FILE}' not found. Please run oauth_handler.py first."
        )

    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(token_data, SCOPES)

    if creds.expiry:
        expiry_utc = creds.expiry.replace(tzinfo=datetime.timezone.utc)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        remaining_seconds = (expiry_utc - now_utc).total_seconds()

        # Only refresh and print when <= 5 minutes remain
        if remaining_seconds <= 300 and creds.refresh_token:
            print("[TOKEN] Refreshing expiring access token...")
            creds.refresh(Request())
            save_tokens_to_json(creds)
            print("[TOKEN] token.json successfully updated.")
    else:
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            save_tokens_to_json(creds)

    return creds


def extract_email_body(raw_data: str) -> tuple[str, str]:
    """Decodes raw base64 RFC 822 email payload into subject and readable text."""
    padded = raw_data + "=" * (-len(raw_data) % 4)
    message = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(padded)
    )

    subject = str(message.get("Subject", "No Subject"))

    plain = message.get_body(preferencelist=("plain",))
    if plain:
        return subject, plain.get_content().strip()

    # Fallback to HTML with tag removal
    html = message.get_body(preferencelist=("html",))
    text = html.get_content() if html else ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", text)
    text = re.sub(r"(?i)<\s*(br|/div|/h[1-6]|/li|/p|/tr)\b[^>]*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    lines = (" ".join(line.split()) for line in unescape(text).splitlines())
    return subject, "\n".join(line for line in lines if line)


def fetch_unread_emails(service) -> list[dict]:
    """Finds all unread emails in the inbox and parses them."""
    results = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread label:INBOX")
        .execute()
    )
    message_summaries = results.get("messages", [])

    if not message_summaries:
        return []

    collected_emails = []
    for item in message_summaries:
        msg_id = item["id"]
        msg_data = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="raw")
            .execute()
        )


        metadata = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["From"],
            )
            .execute()
        )
        from_header = next(
            (
                h["value"]
                for h in metadata.get("payload", {}).get("headers", [])
                if h["name"].lower() == "from"
            ),
            "Unknown",
        )
        sender_email = parseaddr(from_header)[1].casefold()

        subject, body_text = extract_email_body(msg_data["raw"])

        collected_emails.append(
            {
                "id": msg_id,
                "sender": sender_email,
                "subject": subject,
                "body": body_text,
            }
        )

    return collected_emails


def start_trigger_listener(poll_interval: int = 15):
    """Continuously checks tokens, polls Gmail for new emails, and prints incoming triggers."""
    print(
        f"[TRIGGER RUNNING] Connected to oauth_handler.py. Polling inbox every {poll_interval}s..."
    )

    seen_ids: set[str] = set()

    while True:
        try:
            creds = ensure_valid_token_with_expiry_check()
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)

            unread_emails = fetch_unread_emails(service)

            for email_data in unread_emails:
                if email_data["id"] in seen_ids:
                    continue

                seen_ids.add(email_data["id"])

                print("\n" + "=" * 55)
                print(">> [TRIGGER ACTIVATED] New email received!")
                print(f"ID:      {email_data['id']}")
                print(f"Sender:  {email_data['sender']}")
                print(f"Subject: {email_data['subject']}")
                print(f"Body:    {email_data['body'][:140]}...")
                print("=" * 55)

                # Forward the extracted email data to the agent
                agent_response = run_agent(email_data)

                # Print the output returned by the agent
                print("\n" + "-" * 55)
                print("[AGENT RESPONSE RECEIVED]:")
                print(agent_response["response"])
                print("-" * 55 + "\n")

            if not unread_emails:
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                print(f"[{current_time}] No new unread emails. Waiting...")

        except HttpError as err:
            print(f"[GMAIL API ERROR]: {err}")
        except Exception as e:
            print(f"[UNEXPECTED ERROR]: {e}")

        time.sleep(poll_interval)

if __name__ == "__main__":
    start_trigger_listener(poll_interval=15)