"""Postgres connection + generic upsert helper.

Uses plain psycopg2 (no ORM) — the schema is small and stable enough that
raw SQL is more transparent than an ORM layer for a project this size.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Sequence

import psycopg2
import psycopg2.extras

from etl.config import require_database_url

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
UNDERSTAT_TEAM_SEED_PATH = (
    Path(__file__).resolve().parent.parent / "db" / "seed_understat_team_map.sql"
)


@contextmanager
def get_connection():
    conn = psycopg2.connect(require_database_url())
    try:
        yield conn
    finally:
        conn.close()


def apply_schema(conn) -> None:
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def apply_understat_team_seed(conn) -> None:
    """Idempotent (ON CONFLICT DO UPDATE) — safe to call every historical run."""
    sql = UNDERSTAT_TEAM_SEED_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def get_understat_team_name_map(conn) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("SELECT understat_team_name, team_code FROM understat_team_name_map")
        return dict(cur.fetchall())


def upsert(
    conn,
    table: str,
    columns: Sequence[str],
    rows: Iterable[tuple],
    conflict_columns: Sequence[str],
    has_updated_at: bool = True,
) -> int:
    """Bulk INSERT ... ON CONFLICT (conflict_columns) DO UPDATE for every other column.

    Returns the number of rows sent (not necessarily the number changed —
    Postgres upserts don't report that distinction cheaply).
    """
    rows = list(rows)
    if not rows:
        return 0

    update_columns = [c for c in columns if c not in conflict_columns]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
    if has_updated_at:
        set_clause += ", updated_at = now()"

    query = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s "
        f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {set_clause}"
    )

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)
    conn.commit()
    return len(rows)


RAW_SNAPSHOTS_RETENTION_PER_SOURCE = 14


def insert_raw_snapshot(conn, source: str, payload) -> None:
    """Insert one snapshot, then prune old ones for that source.

    Without this, this table grows unbounded: a bootstrap-static snapshot
    alone is ~1.3MB, so at one insert/night with no pruning it would hit
    ~475MB/year — most of Neon's entire 0.5GB free-tier cap, from this one
    table alone. Keeping only the most recent N per source is plenty for
    the table's actual purpose (debugging a recent bad run) — reprocessing
    from scratch should re-fetch live from the free official API instead
    of relying on old snapshots.
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO raw_snapshots (source, payload) VALUES (%s, %s)",
            (source, psycopg2.extras.Json(payload)),
        )
        cur.execute(
            """
            DELETE FROM raw_snapshots
            WHERE source = %s
              AND id NOT IN (
                  SELECT id FROM raw_snapshots
                  WHERE source = %s
                  ORDER BY fetched_at DESC
                  LIMIT %s
              )
            """,
            (source, source, RAW_SNAPSHOTS_RETENTION_PER_SOURCE),
        )
    conn.commit()


def start_etl_run(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO etl_runs (status) VALUES ('running') RETURNING id"
        )
        run_id = cur.fetchone()[0]
    conn.commit()
    return run_id


def finish_etl_run(
    conn,
    run_id: int,
    status: str,
    detail: str | None = None,
    teams_upserted: int = 0,
    players_upserted: int = 0,
    fixtures_upserted: int = 0,
    gameweek_stats_upserted: int = 0,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE etl_runs
            SET finished_at = now(),
                status = %s,
                detail = %s,
                teams_upserted = %s,
                players_upserted = %s,
                fixtures_upserted = %s,
                gameweek_stats_upserted = %s
            WHERE id = %s
            """,
            (
                status,
                detail,
                teams_upserted,
                players_upserted,
                fixtures_upserted,
                gameweek_stats_upserted,
                run_id,
            ),
        )
    conn.commit()
