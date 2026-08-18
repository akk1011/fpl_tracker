"""Unit tests for etl/db.py's SQL-building logic.

Uses a fake connection/cursor instead of a real Postgres instance — these
tests check the generated SQL and call shape, not actual DB execution.
"""
from unittest.mock import MagicMock, patch

from etl import db


class FakeCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_upsert_returns_zero_for_empty_rows():
    conn = FakeConn()
    result = db.upsert(conn, "teams", ("id", "name"), [], conflict_columns=("id",))
    assert result == 0
    assert conn.committed is False


@patch("etl.db.psycopg2.extras.execute_values")
def test_upsert_builds_expected_sql_and_commits(mock_execute_values):
    conn = FakeConn()
    rows = [(1, "Arsenal"), (2, "Chelsea")]

    result = db.upsert(conn, "teams", ("id", "name"), rows, conflict_columns=("id",))

    assert result == 2
    assert conn.committed is True
    mock_execute_values.assert_called_once()
    _, query, passed_rows = mock_execute_values.call_args[0]
    assert "INSERT INTO teams (id, name)" in query
    assert "ON CONFLICT (id) DO UPDATE SET" in query
    assert "name = EXCLUDED.name" in query
    assert "updated_at = now()" in query
    assert "id = EXCLUDED.id" not in query  # conflict column must not self-update
    assert passed_rows == rows


@patch("etl.db.psycopg2.extras.execute_values")
def test_upsert_omits_updated_at_when_table_lacks_it(mock_execute_values):
    conn = FakeConn()
    rows = [(1, "Defender")]

    db.upsert(
        conn, "positions", ("id", "singular_name"), rows,
        conflict_columns=("id",), has_updated_at=False,
    )

    _, query, _ = mock_execute_values.call_args[0]
    assert "updated_at" not in query


@patch("etl.db.psycopg2.extras.execute_values")
def test_upsert_uses_composite_conflict_target(mock_execute_values):
    conn = FakeConn()
    rows = [(4, 1, 6)]

    db.upsert(
        conn, "player_gameweek_stats", ("player_id", "fixture_id", "total_points"),
        rows, conflict_columns=("player_id", "fixture_id"),
    )

    _, query, _ = mock_execute_values.call_args[0]
    assert "ON CONFLICT (player_id, fixture_id) DO UPDATE SET" in query
    assert "total_points = EXCLUDED.total_points" in query
