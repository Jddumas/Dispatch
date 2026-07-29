"""SQL agent node: natural language -> safe SQL -> natural language answer."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState, build_history, last_human_message
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

customers (id, name, email, created_at, loyalty_tier, region, account_status, preferred_contact, signup_source)
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
        return f"${value:,.2f}"
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
        def _row_label(row: dict) -> str:
            for key in ("name", "customer_name", "product_name", "category"):
                if row.get(key):
                    return str(row[key])
            if row.get("id") is not None:
                return str(row["id"])
            return str(row.get(keys[0], ""))

        if len(rows) == 1:
            label = _row_label(rows[0])
            value = rows[0].get(keys[-1], "")
            phrase = cleaned.replace(" has the ", " with the ")
            if len(keys) == 1:
                return f"The {phrase} is {label}."
            return f"The {phrase} is {label} ({_format_value(value)})."
        parts = []
        for row in rows:
            label = _row_label(row)
            value = row.get(keys[-1], "")
            parts.append(f"- **{label}** ({_format_value(value)})")
        return f"Here are the {cleaned}:\n" + "\n".join(parts)

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
        if "name" in row:
            name = _format_value(row["name"])
            other_pairs = [
                f"{k}: {_format_value(v)}" for k, v in row.items() if k != "name"
            ]
            line = f"- **{name}**" + (f" ({', '.join(other_pairs)})" if other_pairs else "")
        else:
            pairs = [f"{k}: {_format_value(v)}" for k, v in row.items()]
            line = f"- {', '.join(pairs)}"
        parts.append(line)
    return f"Found {len(rows)} records for '{cleaned}':\n" + "\n".join(parts)


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
    history = build_history(messages)
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


def _is_customer_profile_question(question: str) -> bool:
    """Detect natural-language requests for a single customer's 360° summary."""
    return _parse_customer_identifier(question) != (None, None)


def _parse_customer_identifier(question: str) -> tuple[str | None, str | None]:
    """Extract either a customer id or a name from a profile question."""
    q = question.strip().rstrip(".?")

    # Explicit "customer <id>" or "customer #<id>" anywhere in the question.
    m = re.search(r"\bcustomer\s*(?:id|#)?\s*(\d+)\b", q, re.IGNORECASE)
    if m:
        return "id", m.group(1)

    # Phrase-based capture. Remainder is either a number or a name.
    prefixes = [
        r"who is\s+",
        r"tell me about\s+(?:the\s+)?",
        r"summary of\s+(?:the\s+)?",
        r"profile of\s+(?:the\s+)?",
        r"info on\s+(?:the\s+)?",
        r"information on\s+(?:the\s+)?",
        r"what do we know about\s+(?:the\s+)?",
        r"give me (?:a )?summary of\s+(?:the\s+)?",
        r"give me (?:info|information) on\s+(?:the\s+)?",
        r"(?:give (?:me )?)?(?:the )?customer card for\s+",
        r"customer summary for\s+",
        r"(?:show|pull up|get)(?: me)?(?: the)? (?:customer )?(?:card|profile) for\s+",
    ]
    for prefix in prefixes:
        m = re.match(prefix + r"(.+)", q, re.IGNORECASE)
        if m:
            remainder = m.group(1).strip()
            # Strip an optional leading "customer" from the captured text.
            inner = re.match(r"(?:customer\s+(?:id\s+|#?\s*)?)?(.+)", remainder, re.IGNORECASE)
            if inner:
                remainder = inner.group(1).strip()
            if remainder.isdigit():
                return "id", remainder
            if len(remainder) <= 60:
                return "name", remainder
    return None, None


def _resolve_customer(identifier_type: str, value: str) -> list[dict[str, Any]]:
    """Return matching customer id/name rows."""
    if identifier_type == "id":
        return database.execute_query_safe(
            "SELECT id, name FROM customers WHERE id = %s", (int(value),)
        )
    return database.execute_query_safe(
        "SELECT id, name FROM customers WHERE name ILIKE %s",
        (f"%{value}%",),
    )


def _build_customer_profile(customer_id: int) -> dict[str, Any]:
    """Gather a 360° view of a single customer from across all tables."""
    basic_rows = database.execute_query_safe("SELECT * FROM customers WHERE id = %s", (customer_id,))
    if not basic_rows:
        return {}
    basic = basic_rows[0]

    order_stats = database.execute_query_safe(
        "SELECT COALESCE(SUM(total), 0) AS lifetime_spend, COUNT(*) AS order_count, "
        "MAX(created_at) AS last_order_date FROM orders WHERE customer_id = %s AND status != 'cancelled'",
        (customer_id,),
    )[0]

    last_order = database.execute_query_safe(
        "SELECT product_name, status, created_at, total FROM orders "
        "WHERE customer_id = %s AND status != 'cancelled' ORDER BY created_at DESC LIMIT 1",
        (customer_id,),
    )

    tickets = database.execute_query_safe(
        "SELECT COUNT(*) AS open_count FROM support_tickets "
        "WHERE customer_id = %s AND status = 'open'",
        (customer_id,),
    )[0]

    open_ticket_rows = database.execute_query_safe(
        "SELECT subject, created_at FROM support_tickets "
        "WHERE customer_id = %s AND status = 'open' ORDER BY created_at DESC LIMIT 5",
        (customer_id,),
    )

    refunds = database.execute_query_safe(
        "SELECT COUNT(*) AS refund_count, COALESCE(SUM(r.amount), 0) AS refund_total "
        "FROM refunds r JOIN orders o ON r.order_id = o.id "
        "WHERE o.customer_id = %s AND r.status = 'completed'",
        (customer_id,),
    )[0]

    last_note = database.execute_query_safe(
        "SELECT note, created_at FROM account_notes WHERE customer_id = %s "
        "ORDER BY created_at DESC LIMIT 1",
        (customer_id,),
    )

    last_payment = database.execute_query_safe(
        "SELECT p.method, p.status FROM payments p "
        "JOIN orders o ON p.order_id = o.id WHERE o.customer_id = %s "
        "ORDER BY p.created_at DESC LIMIT 1",
        (customer_id,),
    )

    cohort_avg = database.execute_query_safe(
        "SELECT COALESCE(AVG(spend), 0) AS avg_spend FROM ("
        "  SELECT SUM(total) AS spend FROM orders "
        "  WHERE status != 'cancelled' GROUP BY customer_id"
        ") s",
    )[0]

    return {
        "basic": basic,
        "order_stats": order_stats,
        "last_order": last_order[0] if last_order else None,
        "open_tickets": tickets,
        "open_ticket_list": open_ticket_rows,
        "refunds": refunds,
        "last_note": last_note[0] if last_note else None,
        "last_payment": last_payment[0] if last_payment else None,
        "cohort_avg_spend": float(cohort_avg["avg_spend"] or 0),
    }


def _format_customer_profile(profile: dict[str, Any]) -> str:
    """Format a customer 360° profile as 6-10 plain-text lines."""
    if not profile:
        return "Customer not found."
    c = profile["basic"]
    spend = float(profile["order_stats"]["lifetime_spend"] or 0)
    order_count = profile["order_stats"]["order_count"] or 0
    aov = spend / order_count if order_count else 0
    signup = c["created_at"].strftime("%Y-%m-%d")
    tenure = (
        datetime.now(timezone.utc) - c["created_at"].replace(tzinfo=timezone.utc)
    ).days

    last_order = profile["last_order"]
    if last_order:
        date = last_order["created_at"].strftime("%Y-%m-%d")
        last_order_line = (
            f"{last_order['product_name']} on {date} - status: {last_order['status']} "
            f"(${float(last_order['total']):,.2f})"
        )
    else:
        last_order_line = "none"

    open_count = profile["open_tickets"]["open_count"]
    subjects = ", ".join(t["subject"] for t in profile.get("open_ticket_list", []))
    if open_count:
        support_line = f"{open_count} open ticket(s)"
        if subjects:
            support_line += f" ({subjects})"
    else:
        support_line = "no open tickets"

    refund_count = profile["refunds"]["refund_count"]
    refund_total = float(profile["refunds"]["refund_total"] or 0)
    refund_line = (
        f"{refund_count} ({_format_value(refund_total)})" if refund_count else "none"
    )

    lines = [
        f"Customer 360 for {c['name']} (ID {c['id']}):",
        f"Contact: {c['email']}; preferred contact: {c['preferred_contact']}",
        (
            f"Account: {c['account_status']}, {c['loyalty_tier']} tier, region {c['region']}, "
            f"signed up {signup} ({tenure} days ago) via {c['signup_source']}"
        ),
        f"Spend: {_format_value(spend)} across {order_count} order(s); average order {_format_value(aov)}",
        f"Last order: {last_order_line}",
        f"Support: {support_line}",
        f"Refunds: {refund_line}",
    ]

    if profile["last_note"]:
        note = profile["last_note"]
        note_date = note["created_at"].strftime("%Y-%m-%d")
        lines.append(f"Latest note: {note['note']} ({note_date})")

    flags = []
    cohort_avg = profile.get("cohort_avg_spend", 0)
    if open_count >= 2 and refund_count >= 1:
        flags.append("At-risk: multiple open tickets and refund history")
    elif open_count >= 3:
        flags.append("At-risk: high volume of open support tickets")
    if cohort_avg and spend >= cohort_avg * 2:
        flags.append(f"High-value: spend is {spend / cohort_avg:.1f}x the account average (${cohort_avg:,.0f})")
    last_order_date = profile["order_stats"].get("last_order_date")
    if last_order_date and c["account_status"] == "active":
        days_since = (datetime.now(timezone.utc) - last_order_date.replace(tzinfo=timezone.utc)).days
        if days_since > 180:
            flags.append(f"Dormant: no purchase in {days_since} days")
    if flags:
        lines.append("Flags: " + "; ".join(flags))

    return "\n".join(lines)


def run_customer_profile_agent(question: str) -> dict[str, Any]:
    """Resolve a customer and return a plain-text 360° profile."""
    identifier_type, value = _parse_customer_identifier(question)
    if not identifier_type:
        return {
            "query": "",
            "rows": [],
            "answer": "I can look up a customer profile if you provide a customer id or name.",
        }

    matches = _resolve_customer(identifier_type, value)
    if not matches:
        return {
            "query": "",
            "rows": [],
            "answer": f"I couldn't find a customer matching '{value}'.",
        }

    if len(matches) > 1:
        candidates = ", ".join(f"{m['name']} (ID {m['id']})" for m in matches)
        return {
            "query": "",
            "rows": [],
            "answer": f"I found multiple customers matching '{value}': {candidates}. Please be more specific.",
        }

    customer_id = matches[0]["id"]
    profile = _build_customer_profile(customer_id)
    answer = _format_customer_profile(profile)
    return {
        "query": "Customer 360 profile lookup (read-only SELECT statements)",
        "rows": [profile],
        "answer": answer,
    }


def sql_node(state: AgentState) -> dict[str, Any]:
    """Run the SQL agent or customer-profile agent on the latest user message."""
    question = last_human_message(state)
    try:
        if _is_customer_profile_question(question):
            result = run_customer_profile_agent(question)
        else:
            result = run_sql_agent(question, messages=state["messages"])
        return {
            "result": result["answer"],
            "sql_query": result.get("query", ""),
            "data": result.get("rows") or [],
            "sources": [],
        }
    except Exception:
        logger.exception("SQL agent node failed")
        return {
            "result": "I couldn't query the database right now. Please try again later.",
            "sql_query": "",
            "data": [],
            "sources": [],
        }
