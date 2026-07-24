"""Tests for SQL-agent safety helpers."""

from __future__ import annotations

import pytest

from app.agents.sql_agent import _is_safe


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
