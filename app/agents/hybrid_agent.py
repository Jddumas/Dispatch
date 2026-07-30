"""Hybrid agent node: answers questions that require both DB data and policy knowledge."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.sql_agent import run_sql_agent
from app.agents.state import AgentState, last_human_message
from app.config import LLM_MODEL
from app.llm import get_llm
from app.tools.retriever import RAG_DISTANCE_THRESHOLD, retrieve

logger = logging.getLogger(__name__)

_ELIGIBILITY_KEYWORDS = ("eligible", "qualify", "return", "warranty", "refund")


def hybrid_node(state: AgentState) -> dict[str, Any]:
    """Fan out to SQL + RAG, then synthesize both results with a single LLM call."""
    question = last_human_message(state)
    messages = state["messages"]

    is_eligibility = any(kw in question.lower() for kw in _ELIGIBILITY_KEYWORDS)

    # Step 1: get structured DB data.
    # For eligibility questions, hint the SQL agent to include shipping dates.
    # Pass the original question as display_question so _format_sql_answer picks the
    # right format branch (the hint appends "most recent" which would trigger the
    # "most/top" branch and produce the wrong text format).
    sql_question = question
    if is_eligibility:
        sql_question = (
            question
            + " Return the customer's most recent non-cancelled order with these columns:"
            + " o.id AS order_id, o.product_name, o.created_at, o.status, o.total, sh.delivered_at."
            + " Use LEFT JOIN shipping sh ON sh.order_id = o.id."
            + " Do NOT filter by sh.delivered_at or sh.status — include orders that have not yet been delivered."
            + " Order by o.created_at DESC LIMIT 1."
        )
    try:
        sql_result = run_sql_agent(sql_question, messages=messages, display_question=question)
        db_answer = sql_result.get("answer", "No database result.")
        sql_query = sql_result.get("query", "")
        rows = sql_result.get("rows", [])
        data = rows
    except Exception:
        logger.exception("Hybrid agent SQL step failed")
        db_answer = "Database lookup failed."
        sql_query = ""
        rows = []
        data = []

    db_failed = db_answer.startswith(("Database error:", "Database lookup failed."))

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

    # For eligibility questions, derive a complete ruling in Python so the LLM only
    # has to explain it in natural language — never decide eligibility itself.
    ruling: str | None = None
    ref_date: date | None = None
    elapsed_days: int | None = None

    if is_eligibility:
        order_status = ""
        delivered_available = False

        if rows:
            row = rows[0]
            status_val = row.get("status", "")
            order_status = str(status_val).lower() if status_val else ""

            delivered_at_val = row.get("delivered_at")
            if delivered_at_val is not None:
                delivered_available = True
                if hasattr(delivered_at_val, "date"):
                    ref_date = delivered_at_val.date()
                else:
                    try:
                        ref_date = datetime.strptime(str(delivered_at_val)[:10], "%Y-%m-%d").date()
                    except ValueError:
                        delivered_available = False
                if delivered_available and ref_date:
                    elapsed_days = (today - ref_date).days

        if order_status in ("returned", "refunded", "cancelled"):
            ruling = f"Not eligible — this order has already been {order_status}."
        elif not delivered_available and order_status in ("shipped", "processing", "pending"):
            ruling = (
                "Not yet eligible — the order has not been delivered yet. "
                "The return window starts on the delivery date."
            )
        elif not delivered_available:
            ruling = "Cannot determine eligibility — delivery date not recorded."
        elif elapsed_days is not None:
            # Determine policy window from the question type.
            if "warranty" in question.lower():
                policy_days = 365
                policy_label = "1-year warranty"
            else:
                policy_days = 30
                policy_label = "30-day return"
            if elapsed_days < policy_days:
                ruling = (
                    f"Eligible — the order was delivered {elapsed_days} days ago on {ref_date}, "
                    f"which is within the {policy_label} window."
                )
            else:
                ruling = (
                    f"Not eligible — the order was delivered {elapsed_days} days ago on {ref_date}, "
                    f"which exceeds the {policy_label} window."
                )
        else:
            ruling = "Cannot determine eligibility — no order data available."

    # Step 4: build synthesis prompt
    _NO_GREETING = (
        "Do not open with a greeting or the customer's name as a salutation — "
        "respond professionally and directly. "
        "Use the customer's name naturally within the response when relevant. "
    )

    try:
        if ruling:
            synthesis_prompt = (
                f"Today's date: {today_str}\n\n"
                f"Database result:\n{db_answer}\n\n"
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                f"Ruling: {ruling}\n\n"
                "Explain this ruling to the customer using the relevant details from the database "
                "(product name, delivery date) and the applicable policy rule. "
                "Do not contradict or restate the ruling ambiguously — the ruling is final. "
                + _NO_GREETING
                + "Do not use markdown."
            )
        elif is_eligibility:
            # Fallback: should not normally reach here since ruling is always set above
            synthesis_prompt = (
                f"Today's date: {today_str}\n\n"
                f"Database result:\n{db_answer}\n\n"
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                "Answer whether the customer is eligible based on the database result and policy context. "
                + _NO_GREETING
                + "Do not use markdown."
            )
        elif db_failed:
            # Non-eligibility hybrid but DB lookup failed — answer from RAG only.
            synthesis_prompt = (
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                "Answer the question using the policy context provided. Be specific and helpful. "
                + _NO_GREETING
                + "Do not use markdown."
            )
        else:
            # Non-eligibility hybrid: combine DB data with policy/product knowledge.
            synthesis_prompt = (
                f"Today's date: {today_str}\n\n"
                f"Database result:\n{db_answer}\n\n"
                f"Policy/product context:\n{rag_context or 'No relevant policy context found.'}\n\n"
                f"Question: {question}\n\n"
                "Answer the question by combining the database result with the relevant policy or "
                "product context. Be specific, helpful, and concise. "
                + _NO_GREETING
                + "Do not use markdown."
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
