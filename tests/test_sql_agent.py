"""Tests for SQL-agent safety and formatting helpers."""

from __future__ import annotations

import pytest

from app.agents.sql_agent import _format_sql_answer, _is_safe


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM customers",
        "SELECT COUNT(*) FROM orders WHERE status = 'shipped'",
        "SELECT id FROM support_tickets WHERE status = 'open'",
    ],
)
def test_is_safe_accepts_selects(query: str):
    safe, reason = _is_safe(query)
    assert safe is True
    assert reason == ""


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM customers",
        "INSERT INTO customers (name) VALUES ('bob')",
        "UPDATE orders SET status = 'shipped'",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN age INT",
        "TRUNCATE TABLE orders",
    ],
)
def test_is_safe_rejects_mutating_statements(query: str):
    safe, reason = _is_safe(query)
    assert safe is False
    assert reason


def test_is_safe_rejects_multiple_statements():
    safe, reason = _is_safe("SELECT 1; DROP TABLE customers")
    assert safe is False
    assert "Multiple" in reason or "Forbidden" in reason


def test_is_safe_ignores_comments_and_strings():
    # 'delete' inside a string literal and comment should not trigger rejection.
    safe, reason = _is_safe("SELECT * FROM t WHERE note = 'please delete this' -- delete")
    assert safe is True
    assert reason == ""


def test_is_safe_rejects_empty_query():
    safe, reason = _is_safe("")
    assert safe is False
    assert "empty" in reason.lower()


def test_format_count_answer():
    result = _format_sql_answer("How many orders are there?", [{"count": 103}])
    assert "103" in result


def test_format_average_answer():
    result = _format_sql_answer("What is the average order value?", [{"avg": 766.63}])
    assert "$766.63" in result


def test_format_list_with_name_and_id():
    rows = [
        {"id": 2, "name": "Liam Johnson"},
        {"id": 36, "name": "Joseph Scott"},
    ]
    result = _format_sql_answer(
        "Which customers have an open ticket and a returned order?", rows
    )
    assert "**Liam Johnson** (id: 2)" in result
    assert "**Joseph Scott** (id: 36)" in result
    assert "\n- **" in result


def test_format_list_without_name():
    rows = [{"category": "Electronics", "total": 100.0}]
    result = _format_sql_answer("What is total revenue by category?", rows)
    assert "Electronics" in result
    assert "$100.00" in result


def test_format_empty_rows():
    result = _format_sql_answer("Who has an open ticket?", [])
    assert result == "No results found."
