"""Dispatch AI LangGraph router and compiled graph."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agents.action_agent import action_node
from app.agents.rag_agent import rag_node
from app.agents.sql_agent import sql_node
from app.agents.state import AgentState, last_human_message
from app.config import CLASSIFY_MODEL, LLM_MODEL, MAX_INPUT_LENGTH, CHECKPOINT_DB


logger = logging.getLogger(__name__)

ALLOWED_INTENTS = {"sql", "rag", "action", "general"}
BLOCKED_KEYWORDS = ["hack", "exploit", "bypass", "password", "credit card"]

_GRAPH = None
_CHECKPOINTER = None


def _conversation_history(state: AgentState, max_turns: int = 4) -> str:
    """Return the most recent user/assistant turns as context for the classifier."""
    recent = state["messages"][-max_turns * 2 :]
    lines = []
    for msg in recent:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def validate_input(state: AgentState) -> dict:
    """Validate user input and guardrails before classification."""
    user_text = last_human_message(state)
    if not user_text or not user_text.strip():
        logger.warning("Empty user message received")
        return {"intent": "fallback", "result": "Please send a non-empty message."}

    if len(user_text) > MAX_INPUT_LENGTH:
        logger.warning("User message exceeded max length: %d", len(user_text))
        return {
            "intent": "fallback",
            "result": f"Message is too long. Please keep it under {MAX_INPUT_LENGTH} characters.",
        }

    lowered = user_text.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in lowered:
            logger.warning("Blocked keyword detected: %s", keyword)
            return {
                "intent": "fallback",
                "result": "I can't help with that request. Please ask something else.",
            }

    # Clear any stale intent from a previous turn so classify_intent runs fresh.
    return {"intent": ""}


def route_from_validate(state: AgentState) -> str:
    """Route valid input to classification and invalid input to fallback."""
    return "invalid" if state.get("intent") == "fallback" else "valid"


def classify_intent(state: AgentState) -> dict:
    """Classify the latest user message using conversation history as context."""
    user_text = last_human_message(state)
    history = _conversation_history(state)
    prompt = (
        "You are an intent classifier for a support assistant. "
        "Given the conversation history and the latest user message, "
        "classify the intent into exactly one of these categories:\n"
        "- sql: questions about orders, customers, tickets, or database data\n"
        "- rag: questions about company policies, product specs, or troubleshooting\n"
        "- action: requests that require a tool such as weather, notification, or creating a ticket\n"
        "- general: greetings, small talk, or anything else\n\n"
        "Respond with exactly one lowercase word. Do not explain.\n"
        "Allowed responses: sql, rag, action, general\n\n"
        f"Conversation history:\n{history}\n\n"
        f"Latest user message: {user_text}\n"
        "Intent:"
    )

    try:
        llm = (
            ChatOllama(model=CLASSIFY_MODEL, temperature=0.0, num_predict=20)
            .with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip().lower()
        first_word = raw.split()[0] if raw.split() else ""
        intent = "".join(c for c in first_word if c.isalpha())
        if intent not in ALLOWED_INTENTS:
            intent = "general"
        logger.info("Classified intent: %s", intent)
    except Exception as exc:
        logger.exception("Intent classification failed: %s", exc)
        intent = "general"

    return {"intent": intent}


def route(state: AgentState) -> str:
    """Return the name of the next node based on the classified intent."""
    return state.get("intent", "general")


def fallback_node(state: AgentState) -> dict:
    """Return a graceful fallback message."""
    result = state.get("result") or "I'm sorry, I couldn't handle that request. Can you rephrase?"
    logger.info("Falling back with result: %s", result)
    return {"result": result}


def general_node(state: AgentState) -> dict:
    """Answer directly with the LLM, using the full conversation history."""
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=400)
        response = llm.invoke(
            [
                SystemMessage(content="You are a helpful support assistant."),
                *state["messages"],
            ]
        )
        return {"result": response.content}
    except Exception as exc:
        logger.exception("General node failed: %s", exc)
        return {"result": "I'm having trouble responding right now. Please try again."}


def format_response(state: AgentState) -> dict:
    """Append the specialist result as an assistant message."""
    return {"messages": [AIMessage(content=state["result"])]}


def build_graph(checkpointer=None):
    """Build and compile the full multi-agent graph."""
    builder = StateGraph(AgentState)
    builder.add_node("validate", validate_input)
    builder.add_node("classify", classify_intent)
    builder.add_node("sql_agent", sql_node)
    builder.add_node("rag_agent", rag_node)
    builder.add_node("action_agent", action_node)
    builder.add_node("general", general_node)
    builder.add_node("fallback", fallback_node)
    builder.add_node("format", format_response)

    builder.add_edge(START, "validate")
    builder.add_conditional_edges(
        "validate",
        route_from_validate,
        {"invalid": "fallback", "valid": "classify"},
    )
    builder.add_conditional_edges(
        "classify",
        route,
        {
            "sql": "sql_agent",
            "rag": "rag_agent",
            "action": "action_agent",
            "general": "general",
            "fallback": "fallback",
        },
    )
    for node in ["sql_agent", "rag_agent", "action_agent", "general", "fallback"]:
        builder.add_edge(node, "format")
    builder.add_edge("format", END)

    return builder.compile(checkpointer=checkpointer)


def get_graph():
    """Return a singleton compiled graph with a SQLite checkpointer."""
    global _GRAPH, _CHECKPOINTER
    if _GRAPH is None:
        Path(CHECKPOINT_DB).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
        _CHECKPOINTER = SqliteSaver(conn)
        _GRAPH = build_graph(checkpointer=_CHECKPOINTER)
    return _GRAPH


def run_agent(question: str, thread_id: str = "default") -> AgentState:
    """Run the compiled graph against a single user question, persisting state by thread_id."""
    graph = get_graph()
    return graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"configurable": {"thread_id": thread_id}},
    )


def get_thread_history(thread_id: str) -> list[dict[str, str]]:
    """Return the message history for a given thread_id."""
    graph = get_graph()
    snapshot = graph.get_state(config={"configurable": {"thread_id": thread_id}})
    if not snapshot:
        return []
    messages = snapshot.values.get("messages", [])
    return [
        {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
        for m in messages
    ]


if __name__ == "__main__":
    from app.config import setup_logging
    setup_logging()
    questions = [
        "How many customers do we have?",
        "What is the return policy?",
        "What is the weather in London?",
        "Create a support ticket for customer 1 about order 5",
        "Hello!",
    ]
    for question in questions:
        print(f"\nUser: {question}")
        final_state = run_agent(question, thread_id="default")
        print(f"Intent: {final_state['intent']}")
        print(f"Assistant: {final_state['messages'][-1].content}")
