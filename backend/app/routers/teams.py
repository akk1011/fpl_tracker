from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.db import get_db

router = APIRouter(tags=["teams"])


@router.get("/teams")
def list_teams(db: Connection = Depends(get_db)) -> list[dict]:
    query = """
        SELECT t.*, count(p.id) AS squad_size
        FROM teams t
        LEFT JOIN players p ON p.team_id = t.id
        GROUP BY t.id
        ORDER BY t.name ASC
    """
    with db.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


@router.get("/teams/{code}")
def get_team(code: int, db: Connection = Depends(get_db)) -> dict:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM teams WHERE code = %s", (code,))
        team = cur.fetchone()

    if team is None:
        raise HTTPException(404, f"No team with code {code}")

    squad_query = """
        SELECT p.id, p.code, p.web_name, pos.singular_name_short AS position,
               p.now_cost, p.total_points, p.form, p.minutes, p.goals_scored,
               p.assists, p.clean_sheets, p.status
        FROM players p
        JOIN positions pos ON pos.id = p.position_id
        WHERE p.team_id = %s
        ORDER BY pos.id ASC, p.total_points DESC
    """
    with db.cursor() as cur:
        cur.execute(squad_query, (team["id"],))
        squad = cur.fetchall()

    return {**team, "squad": squad}
