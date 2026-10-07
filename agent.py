import os
from dotenv import load_dotenv

from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

load_dotenv()


def build_email_agent(
    model_name: str = "open-mistral-7b", temperature: float = 0.0
) -> Runnable:
    """Builds and returns the runnable email evaluation chain."""
    llm = ChatMistralAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("MISTRAL_API_KEY"),
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an AI email assistant. Analyze the incoming email and summarize its contents.",
        ),
        (
            "human",
            "From: {sender}\nSubject: {subject}\n\nEmail Text:\n{email_text}",
        ),
    ])

    output_parser = StrOutputParser()

    return prompt | llm | output_parser


def run_agent(email_data: dict) -> dict:
    """Receives email data forwarded from trigger.py and processes it."""
    sender = email_data.get("sender", "Unknown")
    subject = email_data.get("subject", "No Subject")
    email_text = email_data.get("body") or email_data.get("text", "")

    print(f"\n[AGENT] Received email from: {sender}")
    print(f"[AGENT] Subject: {subject}")
    print("[AGENT] Processing with Mistral 7B...")

    agent = build_email_agent()

    result = agent.invoke({
        "sender": sender,
        "subject": subject,
        "email_text": email_text,
    })

    return {
        "sender": sender,
        "subject": subject,
        "response": result,
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