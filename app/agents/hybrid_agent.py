"""Hybrid agent node: answers questions that require both DB data and policy knowledge."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
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
    # For eligibility questions, hint the SQL agent to include dates so the LLM can evaluate policy windows.
    _ELIGIBILITY_KEYWORDS = ("eligible", "qualify", "return", "warranty", "refund")
    sql_question = question
    if any(kw in question.lower() for kw in _ELIGIBILITY_KEYWORDS):
        sql_question = (
            question
            + " Return the customer's most recent non-cancelled order with these columns:"
            + " o.id AS order_id, o.product_name, o.created_at, o.status, o.total, sh.delivered_at."
            + " Use LEFT JOIN shipping sh ON sh.order_id = o.id."
            + " Do NOT filter by sh.delivered_at or sh.status — include orders that have not yet been delivered."
            + " Order by o.created_at DESC LIMIT 1."
        )
    try:
        sql_result = run_sql_agent(sql_question, messages=messages)
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
    today = date.today()
    today_str = today.isoformat()

    # Derive eligibility ruling in Python so the LLM only has to explain it.
    status_match = re.search(r"\bstatus\s*=\s*(\w+)", db_answer)
    order_status = status_match.group(1).lower() if status_match else ""

    delivered_match = re.search(r"\bdelivered_at\s*=\s*(\S+)", db_answer)
    delivered_val = delivered_match.group(1).lower().rstrip(".,") if delivered_match else ""
    delivered_available = delivered_val not in ("", "n/a", "null", "none")

    elapsed_days: int | None = None
    ref_date: date | None = None
    # Use delivered_at for returns; fall back to first date found for warranty.
    date_src = delivered_val if delivered_available else None
    if not date_src:
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", db_answer)
        date_src = m.group(1) if m else None
    if date_src:
        try:
            ref_date = datetime.strptime(date_src[:10], "%Y-%m-%d").date()
            elapsed_days = (today - ref_date).days
        except ValueError:
            pass

    if order_status in ("returned", "refunded", "cancelled"):
        ruling = f"Not eligible — this order has already been {order_status}."
    elif not delivered_available and order_status in ("shipped", "processing", "pending"):
        ruling = (
            "Not yet eligible — the order has not been delivered yet. "
            "The return window starts on the delivery date."
        )
    elif not delivered_available:
        ruling = "Cannot determine eligibility — delivery date not recorded."
    else:
        ruling = None  # LLM will apply the policy window to elapsed_days

    try:
        if ruling:
            synthesis_prompt = (
                f"Today's date: {today_str}\n\n"
                f"Database result:\n{db_answer}\n\n"
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                f"Ruling: {ruling}\n\n"
                "Explain this ruling to the customer using the relevant details from the database result "
                "and the applicable policy rule. Do not contradict the ruling. Do not use markdown."
            )
        else:
            elapsed_note = (
                f"\n\nPre-computed: {elapsed_days} days have elapsed since {ref_date} (today is {today_str})."
                if elapsed_days is not None else ""
            )
            synthesis_prompt = (
                f"Today's date: {today_str}\n\n"
                f"Database result:\n{db_answer}{elapsed_note}\n\n"
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                "Using the pre-computed elapsed days and the policy window from the policy context, "
                "answer whether the customer is eligible. "
                "If elapsed days < policy window (e.g. < 30 for returns, < 365 for warranty), say 'Yes, eligible.' "
                "If elapsed days >= policy window, say 'No, not eligible.' "
                "After your opening phrase, explain with the date, elapsed days, and policy rule. "
                "Do not use markdown."
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
