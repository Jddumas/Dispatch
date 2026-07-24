"""PostgreSQL database utilities for the Dispatch AI project."""

import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

CONNECTION_ARGS = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "support_agent"),
    "user": os.getenv("PGUSER", "agent"),
    "password": os.getenv("PGPASSWORD", "password"),
}


def get_connection():
    """Return a new psycopg2 connection configured from environment variables."""
    return psycopg2.connect(**CONNECTION_ARGS, cursor_factory=RealDictCursor)


def execute_query(
    query: str, params: tuple[Any, ...] | None = None, *, fetch: bool = True
) -> list[dict[str, Any]] | int:
    """Execute a SQL query and return results or the row count.

    Parameters are safely passed to psycopg2 to prevent SQL injection.
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        if fetch:
            return cur.fetchall()
        conn.commit()
        return cur.rowcount


def execute_query_safe(
    query: str, params: tuple[Any, ...] | None = None
) -> list[dict[str, Any]]:
    """Execute a parameterized SELECT-style query and return all rows."""
    return execute_query(query, params, fetch=True)


if __name__ == "__main__":
    # Quick sanity check
    rows = execute_query_safe(
        "SELECT COUNT(*) AS total FROM customers"
    )
    print(rows)
