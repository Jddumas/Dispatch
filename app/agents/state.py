"""Shared state and helpers for Dispatch AI agents."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import add_messages
from typing_extensions import NotRequired, TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    result: str
    sources: list[str]
    sql_query: str
    data: NotRequired[list[dict[str, Any]] | None]


def last_human_message(state: AgentState) -> str:
    """Return the content of the most recent HumanMessage."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def build_history(messages: list[BaseMessage] | None, max_turns: int = 3) -> str:
    """Format recent user questions as context for follow-up queries.

    Only user messages are included — prior assistant answers can confuse
    downstream models when rephrased as context.
    """
    if not messages:
        return ""
    recent = messages[-max_turns * 2 :]
    user_questions = [msg.content for msg in recent if isinstance(msg, HumanMessage)]
    if not user_questions:
        return ""
    return "Previous questions:\n" + "\n".join(f"- {q}" for q in user_questions[-max_turns:])
