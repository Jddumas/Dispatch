"""SQL agent node: natural language -> safe SQL -> natural language answer."""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState, last_human_message
from app.config import LLM_MODEL
from app.llm import get_llm
from app.tools import database

logger = logging.getLogger(__name__)

_FORBIDDEN_KEYWORDS = [
    "drop",
    "delete",
    "insert",
    "update",
    "truncate",
    "alter",
    "create",
    "grant",
    "revoke",
    "replace",
    "merge",
    "exec",
    "execute",
    "call",
    "attach",
    "detach",
    "pragma",
]

_SCHEMA_PROMPT = """You have access to a PostgreSQL database with these tables:

customers (id, name, email, created_at)
products (id, name, category, price, stock_quantity)
orders (id, customer_id, product_name, status, total, created_at)
order_items (id, order_id, product_id, quantity, unit_price, line_total)
payments (id, order_id, amount, method, status, created_at)
shipping (id, order_id, carrier, tracking_number, status, shipped_at, delivered_at)
refunds (id, order_id, amount, reason, status, created_at)
support_tickets (id, customer_id, order_id, subject, description, status, created_at)
account_notes (id, customer_id, note, created_at)

Join tables using their integer id columns (e.g. customers.id = orders.customer_id).
Use aggregate functions like COUNT, SUM, AVG, MIN, MAX and GROUP BY when the question asks for totals, averages, counts, or "per X".
Use DATE_TRUNC('month', created_at) to group by month.
Filter by date with created_at >= NOW() - INTERVAL '30 days' for recent time windows.
Use ILIKE with customer names when matching by name is needed.
Return ONLY the SQL query, nothing else.
Only use SELECT or WITH statements.
Do not use a trailing semicolon.
"""


def _build_history(messages: list[BaseMessage] | None, max_turns: int = 3) -> str:
    """Format the most recent conversation turns for follow-up context."""
    if not messages:
        return ""
    recent = messages[-max_turns * 2 :]
    lines = []
    for msg in recent:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _strip_comments(sql: str) -> str:
    """Remove SQL comments so they cannot mask forbidden keywords."""
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def _remove_string_literals(sql: str) -> str:
    """Replace string literals with empty quotes to avoid false keyword matches."""
    sql = re.sub(r"'[^']*'", "''", sql)
    sql = re.sub(r'"[^"]*"', '""', sql)
    return sql


def _extract_sql(text: str) -> str:
    """Extract SQL from a model response that may include markdown fences."""
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _is_safe(sql: str) -> tuple[bool, str]:
    """Validate that the generated SQL is a single read-only SELECT statement."""
    cleaned = _strip_comments(sql).strip().lower()
    if not cleaned:
        return False, "The generated query is empty."

    tokens = cleaned.split()
    if not tokens or tokens[0] not in ("select", "with"):
        return False, "Only SELECT or WITH statements are allowed."

    # Allow one trailing semicolon, but reject additional statement separators.
    neutral = _remove_string_literals(cleaned).rstrip(";")
    if ";" in neutral:
        return False, "Multiple SQL statements are not allowed."

    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", neutral):
            return False, f"Forbidden keyword '{keyword}' detected."

    return True, ""


def _generate_sql(question: str, history: str = "") -> str:
    history_section = f"Conversation history:\n{history}\n\n" if history else ""
    llm = get_llm(model=LLM_MODEL, temperature=0.0, max_tokens=400).with_retry(
        stop_after_attempt=3, wait_exponential_jitter=True
    )
    messages = [
        SystemMessage(content="You are a careful PostgreSQL expert."),
        HumanMessage(content=f"{history_section}{_SCHEMA_PROMPT}\n\nQuestion: {question}"),
    ]
    response = llm.invoke(messages)
    return _extract_sql(response.content)


def _format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        return f"${value:,.2f}" if value > 1 else f"{value:.2f}"
    return str(value)


def _clean_question(question: str) -> str:
    """Strip question words so the remainder can be used in a statement."""
    q = question.lower().strip().rstrip(".?")
    prefixes = [
        "how many", "what is", "what are", "who are", "which",
        "list", "show", "give me", "find", "tell me",
    ]
    for prefix in prefixes:
        if q.startswith(prefix):
            q = q[len(prefix):].strip()
            break
    suffixes = ["are there", "do we have", "is there", "are they", "are the"]
    for suffix in suffixes:
        if q.endswith(suffix):
            q = q[: -len(suffix)].strip()
            break
    # Remove common leading articles and perfect-tense participles.
    for fragment in ("the ", "a ", "an ", "have been ", "has been "):
        if q.startswith(fragment):
            q = q[len(fragment):].strip()
    # Drop "have been" / "has been" anywhere in the phrase for cleaner statements.
    q = q.replace(" have been ", " ").replace(" has been ", " ")
    return q


def _format_sql_answer(question: str, rows: list[dict[str, Any]]) -> str:
    """Format SQL rows into a concise answer without a second LLM call."""
    if not rows:
        return "No results found."

    q = question.lower()
    cleaned = _clean_question(question)
    keys = list(rows[0].keys())

    # Count / how-many queries
    if "how many" in q or "number of" in q or (len(keys) == 1 and ("count" in keys[0].lower() or "total" in keys[0].lower())):
        if len(rows) == 1:
            value = rows[0][keys[0]]
            return f"There are {_format_value(value)} {cleaned}."
        return f"There are {len(rows)} {cleaned}."

    # Average / aggregate single-value queries
    if "average" in q or "avg" in q or "mean" in q:
        value = rows[0][keys[-1]]
        return f"The {cleaned} is {_format_value(value)}."

    # Most / highest / top / max
    if "most" in q or "highest" in q or "top" in q or "max" in q:
        if len(rows) == 1:
            label = rows[0].get(keys[0], "")
            value = rows[0].get(keys[-1], "")
            phrase = cleaned.replace(" has the ", " with the ")
            if len(keys) == 1:
                return f"The {phrase} is {label}."
            return f"The {phrase} is {label} ({_format_value(value)})."
        parts = []
        for row in rows:
            label = row.get(keys[0], "")
            value = row.get(keys[-1], "")
            parts.append(f"{label} ({_format_value(value)})")
        return f"The top results for {cleaned}: {', '.join(parts)}."

    # Grouped / per / by queries
    if " by " in q or " per " in q or q.startswith(("what is total", "total")):
        parts = []
        for row in rows:
            label = row.get(keys[0], "")
            value = row.get(keys[-1], "")
            parts.append(f"{label}: {_format_value(value)}")
        return f"The {cleaned}: {'; '.join(parts)}."

    # Single record lookup
    if len(rows) == 1:
        pairs = [f"{k} = {_format_value(v)}" for k, v in rows[0].items()]
        return f"The result is {', '.join(pairs)}."

    # General list
    preview = rows[:5]
    parts = []
    for row in preview:
        pairs = [f"{k}={_format_value(v)}" for k, v in row.items()]
        parts.append(", ".join(pairs))
    return f'Found {len(rows)} records matching "{cleaned}". {" | ".join(parts)}.'


def _format_answer(question: str, query: str, rows: list[dict[str, Any]]) -> str:
    """LLM-based fallback for unusual or very large result sets."""
    if not rows:
        return "No results found."

    data_text = "\n".join(str(dict(row)) for row in rows[:20])
    prompt = (
        f"The user asked: {question}\n"
        f"The SQL query used was: {query}\n"
        f"The query returned these results:\n{data_text}\n\n"
        "Summarize the answer in 1-2 natural language sentences. Be concise."
    )
    llm = get_llm(model=LLM_MODEL, temperature=0.0, max_tokens=150).with_retry(
        stop_after_attempt=3, wait_exponential_jitter=True
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def run_sql_agent(question: str, messages: list[BaseMessage] | None = None) -> dict[str, Any]:
    """Generate, validate, execute, and summarize a SQL query."""
    history = _build_history(messages)
    query = _generate_sql(question, history=history)
    safe, reason = _is_safe(query)
    if not safe:
        logger.warning("Unsafe SQL rejected: %s -> %s", query, reason)
        return {
            "query": query,
            "error": reason,
            "answer": f"I cannot run that query because it is not a safe read-only query: {reason}",
        }

    try:
        rows = database.execute_query_safe(query)
    except Exception as exc:
        logger.exception("Database query failed")
        return {
            "query": query,
            "error": str(exc),
            "answer": f"Database error: {exc}",
        }

    answer = _format_sql_answer(question, rows)
    return {"query": query, "rows": rows, "answer": answer}


def sql_node(state: AgentState) -> dict[str, Any]:
    """Run the SQL agent on the latest user message and conversation history."""
    question = last_human_message(state)
    try:
        result = run_sql_agent(question, messages=state["messages"])
        return {
            "result": result["answer"],
            "sql_query": result.get("query", ""),
            "data": result.get("rows") or [],
        }
    except Exception:
        logger.exception("SQL agent node failed")
        return {
            "result": "I couldn't query the database right now. Please try again later.",
            "sql_query": "",
            "data": [],
        }
