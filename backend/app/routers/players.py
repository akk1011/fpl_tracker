from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection

from app.db import get_db
from app.scoring import compute_points_breakdown, sum_breakdowns

router = APIRouter(tags=["players"])

# Whitelisted sort columns only — never interpolate user input directly
# into an ORDER BY clause.
_SORTABLE_COLUMNS = {
    "total_points": "p.total_points",
    "now_cost": "p.now_cost",
    "form": "p.form",
    "selected_by_percent": "p.selected_by_percent",
    "goals_scored": "p.goals_scored",
    "assists": "p.assists",
    "expected_goals": "p.expected_goals",
    "expected_assists": "p.expected_assists",
    "ict_index": "p.ict_index",
    "defensive_contribution": "p.defensive_contribution",
    "minutes": "p.minutes",
}

_PLAYER_LIST_COLUMNS = """
    p.id, p.code, p.web_name, p.first_name, p.second_name,
    t.short_name AS team_short_name, t.name AS team_name,
    pos.singular_name_short AS position,
    p.now_cost, p.total_points, p.event_points, p.form,
    p.selected_by_percent, p.minutes, p.goals_scored, p.assists,
    p.clean_sheets, p.expected_goals, p.expected_assists,
    p.expected_goals_conceded, p.ict_index, p.bonus, p.bps,
    p.defensive_contribution, p.status, p.news
"""


@router.get("/players")
def list_players(
    position: str | None = Query(None, description="GKP, DEF, MID, or FWD"),
    team: str | None = Query(None, description="Team short_name, e.g. ARS"),
    sort: str = Query("total_points"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=800),
    db: Connection = Depends(get_db),
) -> list[dict]:
    if sort not in _SORTABLE_COLUMNS:
        raise HTTPException(400, f"Invalid sort column. Choose from: {sorted(_SORTABLE_COLUMNS)}")

    where_clauses = []
    params: list = []
    if position:
        where_clauses.append("pos.singular_name_short = %s")
        params.append(position.upper())
    if team:
        where_clauses.append("t.short_name = %s")
        params.append(team.upper())
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sort_column = _SORTABLE_COLUMNS[sort]
    order_sql = "ASC" if order == "asc" else "DESC"

    query = f"""
        SELECT {_PLAYER_LIST_COLUMNS}
        FROM players p
        JOIN teams t ON t.id = p.team_id
        JOIN positions pos ON pos.id = p.position_id
        {where_sql}
        ORDER BY {sort_column} {order_sql} NULLS LAST
        LIMIT %s
    """
    params.append(limit)

    with db.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


@router.get("/players/{code}")
def get_player(code: int, db: Connection = Depends(get_db)) -> dict:
    query = """
        SELECT p.*, t.short_name AS team_short_name, t.name AS team_name,
               pos.singular_name_short AS position, pos.singular_name AS position_full
        FROM players p
        JOIN teams t ON t.id = p.team_id
        JOIN positions pos ON pos.id = p.position_id
        WHERE p.code = %s
    """
    with db.cursor() as cur:
        cur.execute(query, (code,))
        row = cur.fetchone()

    if row is None:
        raise HTTPException(404, f"No player with code {code}")

    # NOTE: `total_points` etc. above are FPL's own recorded season-total
    # fields — pre-season (before this season's GW1), these still carry
    # forward *last* season's final totals (confirmed directly in Phase 1),
    # not this season's (0 games played so far). points_breakdown_this_season
    # is computed independently by summing this season's actual played
    # matches, so it correctly reads 0 pre-season rather than echoing last
    # season's stale numbers under a "this season" label. It is NOT computed
    # by running compute_points_breakdown on the aggregate `players` row
    # directly — that arithmetic doesn't distribute over a season total
    # (see the warning in app/scoring.py; caught live via a real mismatch:
    # 175 vs. recorded 239 for one real player during Phase 2 testing).
    gameweeks_query = """
        SELECT pgs.*
        FROM player_gameweek_stats pgs
        JOIN players p ON p.id = pgs.player_id
        WHERE p.code = %s
    """
    with db.cursor() as cur:
        cur.execute(gameweeks_query, (code,))
        gameweek_rows = cur.fetchall()

    per_match_breakdowns = [
        compute_points_breakdown(gw_row, row["position"]) for gw_row in gameweek_rows
    ]
    season_breakdown = sum_breakdowns(per_match_breakdowns)

    return {
        **row,
        "matches_played_this_season": len(gameweek_rows),
        "points_breakdown_this_season": season_breakdown,
    }


@router.get("/players/{code}/gameweeks")
def get_player_gameweeks(code: int, db: Connection = Depends(get_db)) -> list[dict]:
    query = """
        SELECT pgs.*, t_opp.short_name AS opponent_short_name, pos.singular_name_short AS position,
               gw.name AS gameweek_name
        FROM player_gameweek_stats pgs
        JOIN players p ON p.id = pgs.player_id
        JOIN positions pos ON pos.id = p.position_id
        JOIN gameweeks gw ON gw.id = pgs.gameweek_id
        LEFT JOIN teams t_opp ON t_opp.id = pgs.opponent_team_id
        WHERE p.code = %s
        ORDER BY pgs.gameweek_id ASC
    """
    with db.cursor() as cur:
        cur.execute(query, (code,))
        rows = cur.fetchall()

    if not rows:
        # Distinguish "player doesn't exist" from "player exists, no gameweeks yet"
        with db.cursor() as cur:
            cur.execute("SELECT 1 FROM players WHERE code = %s", (code,))
            if cur.fetchone() is None:
                raise HTTPException(404, f"No player with code {code}")
        return []

    for row in rows:
        row["points_breakdown"] = compute_points_breakdown(row, row["position"])
    return rows
