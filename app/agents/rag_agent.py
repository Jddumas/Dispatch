"""RAG agent node: answer questions from the indexed knowledge base."""

from app.agents.state import AgentState, last_human_message
from app.tools import retriever


def rag_node(state: AgentState) -> dict[str, str]:
    """Retrieve context and answer the user's question from the knowledge base."""
    question = last_human_message(state)
    answer = retriever.answer(question, k=3)
    return {"result": answer["answer"]}
