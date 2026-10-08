import os
from dotenv import load_dotenv

from graph import build_email_graph

load_dotenv()


def build_email_agent():
    """Builds and returns the runnable email evaluation agent (LangGraph workflow)."""
    return build_email_graph()


def run_agent(email_data: dict) -> dict:
    """Receives email data forwarded from trigger.py and processes it."""
    sender = email_data.get("sender", "Unknown")
    subject = email_data.get("subject", "No Subject")
    email_text = email_data.get("body") or email_data.get("text", "")
    email_id = email_data.get("id", "")

    print(f"\n[AGENT] Received email from: {sender}")
    print(f"[AGENT] Subject: {subject}")
    print("[AGENT] Processing through email agent...")

    agent = build_email_agent()
    initial_state = {
        "id": email_id,
        "sender": sender,
        "subject": subject,
        "text": email_text,
        "is_spam": False,
        "spam_reason": "",
        "summary": "",
    }

    final_state = agent.invoke(initial_state)

    if final_state.get("is_spam"):
        output_response = (
            f"[SPAM DETECTED] Email will not be summarized.\n"
            f"Reason: {final_state.get('spam_reason')}"
        )
    else:
        output_response = final_state.get("summary", "No summary generated.")

    return {
        "sender": sender,
        "subject": subject,
        "response": output_response,
    }


if __name__ == "__main__":
    sample_email = {
        "sender": "test@example.com",
        "subject": "Integration Test",
        "body": "Hello, this is a test email to verify the agent connection.",
    }

    report = run_agent(sample_email)

    print("=" * 50)
    print("FINAL EVALUATION REPORT:")
    print("=" * 50)
    print(report["response"])