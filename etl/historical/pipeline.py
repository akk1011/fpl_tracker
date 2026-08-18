"""Orchestrates one historical season's backfill: fetch -> transform -> load.

Manual/on-demand, not part of the nightly cron — historical data doesn't
change once ingested. Entry point:

    python -m etl.historical.pipeline --season 2025-26
    python -m etl.historical.pipeline --all      # every season in HISTORICAL_SEASONS

Per the approved plan, --all is a hard-gated future step: run one season at
a time, measure real Postgres table sizes, and only then scale up.
"""
from __future__ import annotations

import argparse
import logging

import psycopg2.extras

from etl import db
from etl.config import HISTORICAL_SEASONS
from etl.historical import transform, understat
from etl.historical.vaastav_client import fetch_csv, fetch_understat_team_file

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _with_json_raw(row: tuple) -> tuple:
    """The last element of every historical row tuple is a plain dict (the
    raw CSV row) — wrap it for psycopg2 to adapt as JSONB. Kept out of
    etl/historical/transform.py so that module stays free of DB-adapter
    imports, matching the existing etl/transform.py convention."""
    return row[:-1] + (psycopg2.extras.Json(row[-1]),)


def load_teams(conn, season: str, players_rows: list[dict]) -> tuple[int, dict[int, int]]:
    """Returns (rows upserted, {season_team_id: team_code})."""
    teams_csv = fetch_csv(season, "teams.csv")
    season_id_to_code: dict[int, int] = {}

    if teams_csv:
        rows = [transform.transform_historical_team(r, season) for r in teams_csv]
        for r in rows:
            as_dict = dict(zip(transform.HISTORICAL_TEAM_COLUMNS, r))
            if as_dict["season_team_id"] is not None:
                season_id_to_code[as_dict["season_team_id"]] = as_dict["team_code"]
    else:
        # No teams.csv this season (confirmed: absent 2016-17..2018-19) —
        # recover team_code/season_team_id pairs from players_raw.csv itself.
        distinct_teams: dict[int, int] = {}
        for p in players_rows:
            season_team_id = transform.to_int(p.get("team"))
            team_code = transform.to_int(p.get("team_code"))
            if season_team_id is not None and team_code is not None:
                distinct_teams[season_team_id] = team_code
        rows = [
            transform.transform_historical_team_minimal(season, code, season_id)
            for season_id, code in distinct_teams.items()
        ]
        season_id_to_code = distinct_teams

    upserted = db.upsert(
        conn, "historical_teams", transform.HISTORICAL_TEAM_COLUMNS,
        [_with_json_raw(r) for r in rows], conflict_columns=("season", "team_code"),
        has_updated_at=False,
    )
    log.info("[%s] Loaded %d historical teams", season, upserted)
    return upserted, season_id_to_code


def load_players(conn, season: str, players_csv: list[dict]) -> tuple[int, dict[int, int]]:
    """Returns (rows upserted, {season_element_id: player_code})."""
    rows = [transform.transform_historical_player(r, season) for r in players_csv]
    element_to_code: dict[int, int] = {}
    for r in rows:
        as_dict = dict(zip(transform.HISTORICAL_PLAYER_COLUMNS, r))
        if as_dict["season_element_id"] is not None:
            element_to_code[as_dict["season_element_id"]] = as_dict["player_code"]

    upserted = db.upsert(
        conn, "historical_players", transform.HISTORICAL_PLAYER_COLUMNS,
        [_with_json_raw(r) for r in rows], conflict_columns=("season", "player_code"),
        has_updated_at=False,
    )
    log.info("[%s] Loaded %d historical players", season, upserted)
    return upserted, element_to_code


def load_player_gameweek_stats(
    conn, season: str, element_to_code: dict[int, int], team_id_to_code: dict[int, int],
) -> int:
    merged_gw = fetch_csv(season, "gws/merged_gw.csv")
    if not merged_gw:
        log.warning("[%s] No merged_gw.csv found — skipping gameweek stats", season)
        return 0

    rows = []
    skipped_unresolved = 0
    for raw_row in merged_gw:
        element_id = transform.to_int(raw_row.get("element"))
        player_code = element_to_code.get(element_id)
        if player_code is None:
            skipped_unresolved += 1
            continue
        opponent_id = transform.to_int(raw_row.get("opponent_team"))
        opponent_code = team_id_to_code.get(opponent_id)
        rows.append(
            transform.transform_historical_player_gameweek_stat(
                raw_row, season, player_code, opponent_code
            )
        )

    if skipped_unresolved:
        log.warning(
            "[%s] Skipped %d gameweek rows with no resolvable player_code",
            season, skipped_unresolved,
        )

    upserted = db.upsert(
        conn, "historical_player_gameweek_stats",
        transform.HISTORICAL_PLAYER_GAMEWEEK_STATS_COLUMNS, rows,
        conflict_columns=("season", "player_code", "fixture_season_id"),
        has_updated_at=False,
    )
    log.info("[%s] Loaded %d historical player-gameweek stat rows", season, upserted)
    return upserted


def load_understat_player_stats(conn, season: str, element_to_code: dict[int, int]) -> int:
    understat_players = fetch_csv(season, "understat/understat_player.csv")
    if not understat_players:
        log.info("[%s] No understat_player.csv — skipping Understat player stats", season)
        return 0

    id_dict_rows = fetch_csv(season, "id_dict.csv")
    understat_to_element = (
        understat.build_understat_to_season_element_map(id_dict_rows) if id_dict_rows else {}
    )
    if not id_dict_rows:
        log.info(
            "[%s] No id_dict.csv this season — Understat player rows stored unlinked (player_code NULL)",
            season,
        )

    rows = []
    for raw_row in understat_players:
        understat_id = transform.to_int(raw_row.get("id"))
        element_id = understat_to_element.get(understat_id)
        player_code = element_to_code.get(element_id) if element_id is not None else None
        rows.append(
            transform.transform_historical_understat_player_stat(raw_row, season, player_code)
        )

    upserted = db.upsert(
        conn, "historical_understat_player_stats",
        transform.HISTORICAL_UNDERSTAT_PLAYER_STATS_COLUMNS,
        [_with_json_raw(r) for r in rows], conflict_columns=("season", "understat_id"),
        has_updated_at=False,
    )
    log.info("[%s] Loaded %d historical Understat player rows", season, upserted)
    return upserted


def load_understat_team_stats(conn, season: str) -> int:
    name_map = db.get_understat_team_name_map(conn)
    if not name_map:
        log.warning("[%s] understat_team_name_map is empty — run db/seed_understat_team_map.sql first", season)
        return 0

    total_upserted = 0
    for understat_name, team_code in name_map.items():
        team_rows = fetch_understat_team_file(season, understat_name)
        if not team_rows:
            continue  # expected: this club may not exist / not be in the PL that season
        rows = [
            transform.transform_historical_understat_team_stat(r, season, team_code)
            for r in team_rows
        ]
        total_upserted += db.upsert(
            conn, "historical_understat_team_stats",
            transform.HISTORICAL_UNDERSTAT_TEAM_STATS_COLUMNS,
            [_with_json_raw(r) for r in rows],
            conflict_columns=("season", "team_code", "match_date"),
            has_updated_at=False,
        )
    log.info("[%s] Loaded %d historical Understat team-match rows", season, total_upserted)
    return total_upserted


def run_season(conn, season: str) -> dict:
    log.info("=== Backfilling season %s ===", season)
    players_csv = fetch_csv(season, "players_raw.csv")
    if not players_csv:
        raise RuntimeError(f"No players_raw.csv for season {season} — cannot proceed")

    teams_upserted, team_id_to_code = load_teams(conn, season, players_csv)
    players_upserted, element_to_code = load_players(conn, season, players_csv)
    gameweek_stats_upserted = load_player_gameweek_stats(
        conn, season, element_to_code, team_id_to_code
    )
    understat_player_upserted = load_understat_player_stats(conn, season, element_to_code)
    understat_team_upserted = load_understat_team_stats(conn, season)

    return {
        "teams": teams_upserted,
        "players": players_upserted,
        "gameweek_stats": gameweek_stats_upserted,
        "understat_player": understat_player_upserted,
        "understat_team": understat_team_upserted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical FPL data from vaastav's archive")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--season", help="Single season to backfill, e.g. 2025-26")
    group.add_argument("--all", action="store_true", help="Backfill every season in HISTORICAL_SEASONS")
    args = parser.parse_args()

    seasons = HISTORICAL_SEASONS if args.all else [args.season]

    with db.get_connection() as conn:
        db.apply_schema(conn)
        db.apply_understat_team_seed(conn)
        for season in seasons:
            summary = run_season(conn, season)
            log.info("[%s] Summary: %s", season, summary)


if __name__ == "__main__":
    main()
