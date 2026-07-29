"""Hybrid agent node: answers questions that require both DB data and policy knowledge."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.sql_agent import run_sql_agent
from app.agents.state import AgentState, last_human_message
from app.config import LLM_MODEL
from app.llm import get_llm
from app.tools.retriever import RAG_DISTANCE_THRESHOLD, retrieve

logger = logging.getLogger(__name__)


def hybrid_node(state: AgentState) -> dict[str, Any]:
    """Fan out to SQL + RAG, then synthesize both results with a single LLM call."""
    question = last_human_message(state)
    messages = state["messages"]

    # Step 1: get structured DB data
    try:
        sql_result = run_sql_agent(question, messages=messages)
        db_answer = sql_result.get("answer", "No database result.")
        sql_query = sql_result.get("sql_query", "")
        data = sql_result.get("data", [])
    except Exception:
        logger.exception("Hybrid agent SQL step failed")
        db_answer = "Database lookup failed."
        sql_query = ""
        data = []

    # Step 2: retrieve policy/product context
    try:
        matches = retrieve(question, k=3)
        relevant = [m for m in matches if m["distance"] <= RAG_DISTANCE_THRESHOLD]
        rag_context = "\n\n---\n\n".join(m["text"] for m in relevant)
        sources = list({m["metadata"]["title"] for m in relevant})
    except Exception:
        logger.exception("Hybrid agent RAG step failed")
        rag_context = ""
        sources = []

    # Step 3: synthesize
    try:
        synthesis_prompt = (
            f"Database result:\n{db_answer}\n\n"
            f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
            f"Question: {question}\n\n"
            "Answer in 2-4 sentences. Start with a direct Yes/No or clear conclusion. "
            "Then cite the specific policy clause or date/amount from the data that supports it "
            "(e.g. 'Per our return policy, items must be returned within 30 days in unused condition' "
            "or 'The order was placed on 2026-06-01, which is 27 days ago'). "
            "If either source is empty or not relevant, say so explicitly. Do not use markdown."
        )
        llm = get_llm(model=LLM_MODEL, temperature=0.0, max_tokens=400)
        response = llm.invoke(
            [
                SystemMessage(content="You are a helpful support assistant."),
                HumanMessage(content=synthesis_prompt),
            ]
        )
        result = response.content
    except Exception:
        logger.exception("Hybrid agent synthesis step failed")
        result = db_answer or "I couldn't combine the results right now. Please try again."

    return {
        "result": result,
        "sources": sources,
        "sql_query": sql_query,
        "data": data,
    }
