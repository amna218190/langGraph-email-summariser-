from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from tools import check_email_intent, summarize_email


# 1. State Definition
class EmailProcessingState(TypedDict):
    id: str
    sender: str
    subject: str
    text: str
    is_spam: bool
    spam_reason: str
    summary: str


# 2. Node Functions
def intent_checker_node(state: EmailProcessingState) -> dict:
    """Calls check_email_intent tool to flag spam."""
    print(f"\n[GRAPH NODE: intent_checker] Evaluating '{state['subject']}'...")
    result = check_email_intent.invoke({
        "sender": state["sender"],
        "subject": state["subject"],
        "text": state["text"],
    })
    return {"is_spam": result["is_spam"], "spam_reason": result["reason"]}


def summarizer_node(state: EmailProcessingState) -> dict:
    """Calls summarize_email tool on legitimate emails."""
    print("[GRAPH NODE: summarizer] Summarizing non-spam email...")
    summary_text = summarize_email.invoke({
        "sender": state["sender"],
        "subject": state["subject"],
        "text": state["text"],
    })
    return {"summary": summary_text}



def check_intent_router(
    state: EmailProcessingState,
) -> Literal["summarizer", "end"]:
    """Conditional Edge: routes to summarizer if NOT spam, otherwise terminates."""
    if state["is_spam"]:
        print(f"[ROUTER] Flagged as SPAM ({state['spam_reason']}). Skipping summary.")
        return "end"
    print("[ROUTER] Email is legitimate. Routing to summarizer node.")
    return "summarizer"


# 4. Graph Construction
def build_email_graph():
    workflow = StateGraph(EmailProcessingState)
    workflow.add_node("intent_checker", intent_checker_node)
    workflow.add_node("summarizer", summarizer_node)
    workflow.add_edge(START, "intent_checker")
    workflow.add_conditional_edges(
        "intent_checker",
        check_intent_router,
        {
            "summarizer": "summarizer",
            "end": END,
        },
    )
    workflow.add_edge("summarizer", END)

    return workflow.compile()

compiled_graph = build_email_graph()