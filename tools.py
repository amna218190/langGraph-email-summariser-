import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


def get_tool_llm(temperature: float = 0.0) -> ChatMistralAI:
    return ChatMistralAI(
        model="open-mistral-7b",
        temperature=temperature,
        api_key=os.getenv("MISTRAL_API_KEY"),
    )


@tool
def check_email_intent(sender: str, subject: str, text: str) -> dict:
    """Analyzes an incoming email to determine whether it is SPAM or NOT SPAM.

    Returns a dictionary with 'is_spam' (bool) and 'reason' (str).
    """
    llm = get_tool_llm(temperature=0.0)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an email spam detector. Analyze the sender, subject, and body.\n"
            "Decide if this is SPAM/promotional marketing/phishing OR legitimate personal/work communication.\n"
            "Format your answer EXACTLY as:\n"
            "DECISION: <SPAM or NOT_SPAM>\n"
            "REASON: <Brief explanation>",
        ),
        (
            "human",
            "From: {sender}\nSubject: {subject}\n\nEmail Text:\n{text}",
        ),
    ])

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "sender": sender,
        "subject": subject,
        "text": text[:3000],
    })

    is_spam = "DECISION: SPAM" in result.upper()
    reason = (
        result.split("REASON:")[-1].strip()
        if "REASON:" in result
        else result.strip()
    )

    return {"is_spam": is_spam, "reason": reason}


@tool
def summarize_email(sender: str, subject: str, text: str) -> str:
    """Summarizes a legitimate email, extracting main points, action items, and urgency."""
    llm = get_tool_llm(temperature=0.2)

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an executive email assistant. Summarize this legitimate email concisely.\n"
            "Include:\n"
            "- Core Message (2-3 sentences)\n"
            "- Action Items (if any)\n"
            "- Urgency (Low, Medium, High)",
        ),
        (
            "human",
            "From: {sender}\nSubject: {subject}\n\nEmail Text:\n{text}",
        ),
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "sender": sender,
        "subject": subject,
        "text": text,
    })