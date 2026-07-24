"""Shared state and helpers for Dispatch AI agents."""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    result: str
    sources: list[str]
    sql_query: str


def last_human_message(state: AgentState) -> str:
    """Return the content of the most recent HumanMessage."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""
