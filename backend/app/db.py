"""Per-request Postgres connection helper.

Matches Neon's current documented pattern for serverless clients: open a
connection inside the request handler using the *pooled* (pgbouncer)
connection string, use it, close it before returning — no connection
pooling/reuse across invocations attempted here.

Deliberately separate from etl/db.py rather than shared: this is its own
Vercel project/deployment (see the Phase 2 plan for why Services was not
used), and the connection logic is small enough (~15 lines) that sharing a
package across two independently-deployed projects isn't worth the
packaging complexity. etl/ stays on psycopg2 (already working); this uses
psycopg3, Neon's current headline recommendation for new code.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Loads .env if present; a no-op in CI/Vercel where the real env var is
# already set. Matches etl/config.py's convention.
load_dotenv()


def require_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env locally, or "
            "set the DATABASE_URL env var on the Vercel project (pooled Neon "
            "connection string, the one with '-pooler' in the host)."
        )
    return url


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: yields a connection, closed after the request."""
    conn = psycopg.connect(require_database_url(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
