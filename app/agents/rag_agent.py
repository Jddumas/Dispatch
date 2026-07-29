"""RAG agent node: answer questions from the indexed knowledge base."""

import logging
from typing import Any

from app.agents.state import AgentState, build_history, last_human_message
from app.tools import retriever

logger = logging.getLogger(__name__)


def _extract_sources(matches: list[dict]) -> list[str]:
    """Return unique source titles from retrieved matches."""
    sources = []
    seen = set()
    for match in matches:
        title = match.get("metadata", {}).get("title") or match.get("metadata", {}).get("source", "unknown")
        if title and title not in seen:
            seen.add(title)
            sources.append(title)
    return sources


def rag_node(state: AgentState) -> dict[str, Any]:
    """Retrieve context and answer the user's question from the knowledge base."""
    question = last_human_message(state)
    history = build_history(state["messages"])
    try:
        answer = retriever.answer(question, k=3, conversation_history=history)
        return {
            "result": answer["answer"],
            "sources": _extract_sources(answer.get("matches", [])),
            "sql_query": "",
            "data": [],
        }
    except Exception:
        logger.exception("RAG agent failed")
        return {
            "result": "I couldn't look up that information right now. Please try again later.",
            "sources": [],
            "sql_query": "",
            "data": [],
        }
