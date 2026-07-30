"""PostgreSQL database utilities for the Otto project."""

import os
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

_DATABASE_URL = os.getenv("DATABASE_URL")

SEED_SQL_PATH = Path(__file__).resolve().parents[2] / "data" / "seed_data.sql"

CONNECTION_ARGS = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "support_agent"),
    "user": os.getenv("PGUSER", "agent"),
    "password": os.getenv("PGPASSWORD", "password"),
}


def get_connection():
    """Return a new psycopg2 connection configured from environment variables."""
    if _DATABASE_URL:
        return psycopg2.connect(_DATABASE_URL, cursor_factory=RealDictCursor)
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


def reset_seed_data() -> dict[str, int]:
    """Re-run data/seed_data.sql, dropping and re-creating all seeded tables.

    The feedback table is preserved (it is created separately by init_db.py
    and is not referenced by seed_data.sql).
    """
    sql = SEED_SQL_PATH.read_text(encoding="utf-8")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        conn.commit()
        counts: dict[str, int] = {}
        for table in ("customers", "orders", "support_tickets"):
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
            row = cur.fetchone()
            counts[table] = int(row["n"]) if row else 0
    return counts


if __name__ == "__main__":
    # Quick sanity check
    rows = execute_query_safe(
        "SELECT COUNT(*) AS total FROM customers"
    )
    print(rows)
