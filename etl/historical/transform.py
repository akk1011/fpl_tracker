"""Pure functions: vaastav/Understat CSV row dicts -> row tuples for the DB.

Same philosophy as etl/transform.py: no network, no DB, defensive .get()
throughout because column availability genuinely varies by season (confirmed
directly against real files this session, not assumed). The `raw` element in
each returned tuple is a plain dict — callers wrap it with
psycopg2.extras.Json(...) at upsert time (kept out of this module to match
the existing etl/transform.py convention of staying DB-adapter-free).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

# DEFCON became a real FPL scoring rule starting 2025-26. Season strings
# compare correctly as plain strings for this "YYYY-YY" format since the
# leading 4 digits are the year and seasons only ever increase.
DEFCON_INTRODUCED_SEASON = "2025-26"

POSITION_BY_ELEMENT_TYPE = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))  # some historical CSVs have "0.0"-style ints
    except (ValueError, TypeError):
        return None


def to_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "t")


def parse_kickoff(value: Any) -> str | None:
    """merged_gw.csv kickoff_time is already ISO8601 — pass through, or None."""
    return value or None


def is_defcon_recorded(season: str) -> bool:
    return season >= DEFCON_INTRODUCED_SEASON


HISTORICAL_TEAM_COLUMNS = (
    "season",
    "team_code",
    "season_team_id",
    "name",
    "short_name",
    "strength",
    "strength_overall_home",
    "strength_overall_away",
    "strength_attack_home",
    "strength_attack_away",
    "strength_defence_home",
    "strength_defence_away",
    "raw",
)


def transform_historical_team(row: dict, season: str) -> tuple:
    """`row` is one row from that season's teams.csv."""
    return (
        season,
        to_int(row["code"]),
        to_int(row.get("id")),
        row.get("name"),
        row.get("short_name"),
        to_int(row.get("strength")),
        to_int(row.get("strength_overall_home")),
        to_int(row.get("strength_overall_away")),
        to_int(row.get("strength_attack_home")),
        to_int(row.get("strength_attack_away")),
        to_int(row.get("strength_defence_home")),
        to_int(row.get("strength_defence_away")),
        dict(row),
    )


def transform_historical_team_minimal(season: str, team_code: int, season_team_id: int | None) -> tuple:
    """For pre-2019-20 seasons with no teams.csv: only team_code/id are known
    (recovered from players_raw.csv's own team/team_code columns), everything
    else stays NULL rather than guessed."""
    return (
        season, team_code, season_team_id, None, None,
        None, None, None, None, None, None, None,
        {"note": "no teams.csv for this season; recovered from players_raw.csv only"},
    )


HISTORICAL_PLAYER_COLUMNS = (
    "season",
    "player_code",
    "season_element_id",
    "team_code",
    "first_name",
    "second_name",
    "web_name",
    "position",
    "start_cost",
    "end_cost",
    "total_points",
    "minutes",
    "starts",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    "defcon_recorded",
    "raw",
)


def transform_historical_player(row: dict, season: str) -> tuple:
    """`row` is one row from that season's players_raw.csv.

    now_cost isn't present in every season's players_raw.csv under that
    name — some seasons only have now_cost (current, which for an ended
    season IS the end-of-season cost); cost_change_start lets us recover
    the season's starting cost. Both are treated as best-effort.
    """
    now_cost = to_int(row.get("now_cost"))
    cost_change_start = to_int(row.get("cost_change_start")) or 0
    start_cost = (now_cost - cost_change_start) if now_cost is not None else None

    defcon_available = row.get("defensive_contribution") not in (None, "")

    return (
        season,
        to_int(row["code"]),
        to_int(row.get("id")),
        to_int(row.get("team_code")),
        row.get("first_name"),
        row.get("second_name"),
        row.get("web_name"),
        POSITION_BY_ELEMENT_TYPE.get(to_int(row.get("element_type"))),
        start_cost,
        now_cost,
        to_int(row.get("total_points")),
        to_int(row.get("minutes")),
        to_int(row.get("starts")),
        to_int(row.get("goals_scored")),
        to_int(row.get("assists")),
        to_int(row.get("clean_sheets")),
        to_int(row.get("goals_conceded")),
        to_int(row.get("own_goals")),
        to_int(row.get("penalties_saved")),
        to_int(row.get("penalties_missed")),
        to_int(row.get("yellow_cards")),
        to_int(row.get("red_cards")),
        to_int(row.get("saves")),
        to_int(row.get("bonus")),
        to_int(row.get("bps")),
        to_decimal(row.get("influence")),
        to_decimal(row.get("creativity")),
        to_decimal(row.get("threat")),
        to_decimal(row.get("ict_index")),
        to_decimal(row.get("expected_goals")),
        to_decimal(row.get("expected_assists")),
        to_decimal(row.get("expected_goal_involvements")),
        to_decimal(row.get("expected_goals_conceded")),
        to_int(row.get("clearances_blocks_interceptions")),
        to_int(row.get("recoveries")),
        to_int(row.get("tackles")),
        to_int(row.get("defensive_contribution")),
        is_defcon_recorded(season) and defcon_available,
        dict(row),
    )


HISTORICAL_PLAYER_GAMEWEEK_STATS_COLUMNS = (
    "season",
    "player_code",
    "round",
    "fixture_season_id",
    "opponent_team_code",
    "was_home",
    "total_points",
    "minutes",
    "starts",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    "defcon_recorded",
    "value",
    "selected",
    "transfers_balance",
    "transfers_in",
    "transfers_out",
    "team_h_score",
    "team_a_score",
    "kickoff_time",
)


def transform_historical_player_gameweek_stat(row: dict, season: str, player_code: int, opponent_team_code: int | None) -> tuple:
    """`row` is one row from that season's merged_gw.csv.

    `player_code` and `opponent_team_code` are resolved by the caller
    (season-local `element`/`opponent_team` ids -> stable codes) before
    calling this — this function has no DB/lookup access, by design.
    """
    defcon_available = row.get("defensive_contribution") not in (None, "")
    return (
        season,
        player_code,
        to_int(row["round"]),
        to_int(row["fixture"]),
        opponent_team_code,
        to_bool(row.get("was_home")),
        to_int(row.get("total_points")),
        to_int(row.get("minutes")),
        to_int(row.get("starts")),
        to_int(row.get("goals_scored")),
        to_int(row.get("assists")),
        to_int(row.get("clean_sheets")),
        to_int(row.get("goals_conceded")),
        to_int(row.get("own_goals")),
        to_int(row.get("penalties_saved")),
        to_int(row.get("penalties_missed")),
        to_int(row.get("yellow_cards")),
        to_int(row.get("red_cards")),
        to_int(row.get("saves")),
        to_int(row.get("bonus")),
        to_int(row.get("bps")),
        to_decimal(row.get("influence")),
        to_decimal(row.get("creativity")),
        to_decimal(row.get("threat")),
        to_decimal(row.get("ict_index")),
        to_decimal(row.get("expected_goals")),
        to_decimal(row.get("expected_assists")),
        to_decimal(row.get("expected_goal_involvements")),
        to_decimal(row.get("expected_goals_conceded")),
        to_int(row.get("clearances_blocks_interceptions")),
        to_int(row.get("recoveries")),
        to_int(row.get("tackles")),
        to_int(row.get("defensive_contribution")),
        is_defcon_recorded(season) and defcon_available,
        to_int(row.get("value")),
        to_int(row.get("selected")),
        to_int(row.get("transfers_balance")),
        to_int(row.get("transfers_in")),
        to_int(row.get("transfers_out")),
        to_int(row.get("team_h_score")),
        to_int(row.get("team_a_score")),
        parse_kickoff(row.get("kickoff_time")),
    )


HISTORICAL_UNDERSTAT_TEAM_STATS_COLUMNS = (
    "season", "team_code", "match_date", "was_home", "xg", "xga", "npxg",
    "npxga", "deep", "deep_allowed", "scored", "missed", "xpts", "result", "raw",
)


def transform_historical_understat_team_stat(row: dict, season: str, team_code: int | None) -> tuple:
    """`row` is one row from that season's understat_<TeamName>.csv."""
    return (
        season,
        team_code,
        row.get("date"),
        {"h": True, "a": False}.get(row.get("h_a")),
        to_decimal(row.get("xG")),
        to_decimal(row.get("xGA")),
        to_decimal(row.get("npxG")),
        to_decimal(row.get("npxGA")),
        to_int(row.get("deep")),
        to_int(row.get("deep_allowed")),
        to_int(row.get("scored")),
        to_int(row.get("missed")),
        to_decimal(row.get("xpts")),
        row.get("result"),
        dict(row),
    )


HISTORICAL_UNDERSTAT_PLAYER_STATS_COLUMNS = (
    "season", "understat_id", "player_code", "player_name", "team_title",
    "games", "minutes", "goals", "xg", "assists", "xa", "shots", "key_passes",
    "npg", "npxg", "xg_chain", "xg_buildup", "raw",
)


def transform_historical_understat_player_stat(row: dict, season: str, player_code: int | None) -> tuple:
    """`row` is one row from that season's understat/understat_player.csv."""
    return (
        season,
        to_int(row["id"]),
        player_code,
        row.get("player_name"),
        row.get("team_title"),
        to_int(row.get("games")),
        to_int(row.get("time")),
        to_int(row.get("goals")),
        to_decimal(row.get("xG")),
        to_int(row.get("assists")),
        to_decimal(row.get("xA")),
        to_int(row.get("shots")),
        to_int(row.get("key_passes")),
        to_int(row.get("npg")),
        to_decimal(row.get("npxG")),
        to_decimal(row.get("xGChain")),
        to_decimal(row.get("xGBuildup")),
        dict(row),
    )
