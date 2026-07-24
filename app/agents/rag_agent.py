"""RAG agent node: answer questions from the indexed knowledge base."""

import logging

from app.agents.state import AgentState, last_human_message
from app.tools import retriever


logger = logging.getLogger(__name__)


def rag_node(state: AgentState) -> dict[str, str]:
    """Retrieve context and answer the user's question from the knowledge base."""
    question = last_human_message(state)
    try:
        answer = retriever.answer(question, k=3)
        return {"result": answer["answer"]}
    except Exception as exc:  # noqa: BLE001
        logger.exception("RAG agent failed: %s", exc)
        return {
            "result": "I couldn't look up that information right now. Please try again later."
        }
