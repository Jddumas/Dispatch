"""SQL agent node: natural language -> safe SQL -> natural language answer."""

from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.agents.state import AgentState, last_human_message
from app.config import LLM_MODEL
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
orders (id, customer_id, product_name, status, total, created_at)
support_tickets (id, customer_id, order_id, subject, description, status, created_at)

Write a SQL query to answer the user's question.
Return ONLY the SQL query, nothing else.
Only use SELECT statements.
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
    if not tokens or tokens[0] != "select":
        return False, "Only SELECT statements are allowed."

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
    llm = (
        ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=200)
        .with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
    )
    messages = [
        SystemMessage(content="You are a careful PostgreSQL expert."),
        HumanMessage(content=f"{history_section}{_SCHEMA_PROMPT}\n\nQuestion: {question}"),
    ]
    response = llm.invoke(messages)
    return _extract_sql(response.content)


def _format_answer(question: str, query: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No results found."

    data_text = "\n".join(str(dict(row)) for row in rows[:20])
    prompt = (
        f"The user asked: {question}\n"
        f"The SQL query used was: {query}\n"
        f"The query returned these results:\n{data_text}\n\n"
        "Summarize the answer in 1-2 natural language sentences. Be concise."
    )
    llm = (
        ChatOllama(model=LLM_MODEL, temperature=0.0, num_predict=150)
        .with_retry(stop_after_attempt=3, wait_exponential_jitter=True)
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
    except Exception as exc:  # noqa: BLE001
        logger.exception("Database query failed: %s", exc)
        return {
            "query": query,
            "error": str(exc),
            "answer": f"Database error: {exc}",
        }

    answer = _format_answer(question, query, rows)
    return {"query": query, "rows": rows, "answer": answer}


def sql_node(state: AgentState) -> dict[str, str]:
    """Run the SQL agent on the latest user message and conversation history."""
    question = last_human_message(state)
    try:
        result = run_sql_agent(question, messages=state["messages"])
        return {
            "result": result["answer"],
            "sql_query": result.get("query", ""),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("SQL agent node failed: %s", exc)
        return {
            "result": "I couldn't query the database right now. Please try again later.",
            "sql_query": "",
        }
