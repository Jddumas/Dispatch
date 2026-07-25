"""Idempotent database seeding for Render deployments.

This script runs before uvicorn. If the required tables already exist, it exits
without making changes so repeated container starts are safe.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _connect() -> psycopg2.extensions.connection:
    """Connect using DATABASE_URL if available, otherwise PG* env vars."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "support_agent"),
        user=os.getenv("PGUSER", "agent"),
        password=os.getenv("PGPASSWORD", "password"),
    )


def _already_seeded(conn: psycopg2.extensions.connection) -> bool:
    """Return True if the customers table already exists."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'customers'"
        )
        return cur.fetchone() is not None


def _run_seed_sql(conn: psycopg2.extensions.connection, seed_path: Path) -> None:
    """Execute the seed SQL file as a single transaction."""
    sql = seed_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def main() -> None:
    seed_path = Path(__file__).resolve().parent / "data" / "seed_data.sql"
    logger.info("Connecting to database...")

    conn = _connect()
    try:
        if _already_seeded(conn):
            logger.info("Database already seeded; skipping.")
            return
        logger.info("Seeding database from %s", seed_path)
        _run_seed_sql(conn, seed_path)
        logger.info("Database seeded successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
