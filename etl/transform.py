"""Pure functions: raw FPL API dicts -> row tuples ready for the DB layer.

Deliberately side-effect-free (no network, no DB) so this module is fully
unit-testable without mocking anything. All the "the API gives you a string
that might be empty, a number, or missing" messiness lives here.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def to_decimal(value: Any) -> Decimal | None:
    """FPL sends numeric-ish fields as strings (e.g. "4.5"), sometimes "" or None."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


POSITION_COLUMNS = (
    "id",
    "singular_name",
    "singular_name_short",
    "plural_name",
    "plural_name_short",
    "squad_min_play",
    "squad_max_play",
)


def transform_position(raw: dict) -> tuple:
    return (
        raw["id"],
        raw["singular_name"],
        raw["singular_name_short"],
        raw["plural_name"],
        raw["plural_name_short"],
        to_int(raw.get("squad_min_play")),
        to_int(raw.get("squad_max_play")),
    )


TEAM_COLUMNS = (
    "id",
    "code",
    "name",
    "short_name",
    "strength",
    "strength_overall_home",
    "strength_overall_away",
    "strength_attack_home",
    "strength_attack_away",
    "strength_defence_home",
    "strength_defence_away",
    "played",
    "win",
    "draw",
    "loss",
    "points",
    "position",
)


def transform_team(raw: dict) -> tuple:
    return (
        raw["id"],
        raw["code"],
        raw["name"],
        raw["short_name"],
        to_int(raw.get("strength")),
        to_int(raw.get("strength_overall_home")),
        to_int(raw.get("strength_overall_away")),
        to_int(raw.get("strength_attack_home")),
        to_int(raw.get("strength_attack_away")),
        to_int(raw.get("strength_defence_home")),
        to_int(raw.get("strength_defence_away")),
        to_int(raw.get("played")),
        to_int(raw.get("win")),
        to_int(raw.get("draw")),
        to_int(raw.get("loss")),
        to_int(raw.get("points")),
        to_int(raw.get("position")),
    )


GAMEWEEK_COLUMNS = (
    "id",
    "name",
    "deadline_time",
    "finished",
    "data_checked",
    "is_previous",
    "is_current",
    "is_next",
    "average_entry_score",
    "highest_score",
    "top_element",
    "most_selected",
    "most_transferred_in",
    "most_captained",
    "most_vice_captained",
    "transfers_made",
)


def transform_gameweek(raw: dict) -> tuple:
    return (
        raw["id"],
        raw["name"],
        raw["deadline_time"],
        bool(raw.get("finished")),
        bool(raw.get("data_checked")),
        bool(raw.get("is_previous")),
        bool(raw.get("is_current")),
        bool(raw.get("is_next")),
        to_int(raw.get("average_entry_score")),
        to_int(raw.get("highest_score")),
        to_int(raw.get("top_element")),
        to_int(raw.get("most_selected")),
        to_int(raw.get("most_transferred_in")),
        to_int(raw.get("most_captained")),
        to_int(raw.get("most_vice_captained")),
        to_int(raw.get("transfers_made")),
    )


PLAYER_COLUMNS = (
    "id",
    "code",
    "team_id",
    "position_id",
    "first_name",
    "second_name",
    "web_name",
    "status",
    "news",
    "chance_of_playing_this_round",
    "chance_of_playing_next_round",
    "now_cost",
    "cost_change_start",
    "selected_by_percent",
    "form",
    "points_per_game",
    "value_season",
    "total_points",
    "event_points",
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
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "transfers_in",
    "transfers_out",
    "transfers_in_event",
    "transfers_out_event",
)


def transform_player(raw: dict) -> tuple:
    return (
        raw["id"],
        raw["code"],
        raw["team"],
        raw["element_type"],
        raw.get("first_name"),
        raw.get("second_name"),
        raw["web_name"],
        raw.get("status"),
        raw.get("news"),
        to_int(raw.get("chance_of_playing_this_round")),
        to_int(raw.get("chance_of_playing_next_round")),
        raw["now_cost"],
        to_int(raw.get("cost_change_start")),
        to_decimal(raw.get("selected_by_percent")),
        to_decimal(raw.get("form")),
        to_decimal(raw.get("points_per_game")),
        to_decimal(raw.get("value_season")),
        to_int(raw.get("total_points")),
        to_int(raw.get("event_points")),
        to_int(raw.get("minutes")),
        to_int(raw.get("starts")),
        to_int(raw.get("goals_scored")),
        to_int(raw.get("assists")),
        to_int(raw.get("clean_sheets")),
        to_int(raw.get("goals_conceded")),
        to_int(raw.get("own_goals")),
        to_int(raw.get("penalties_saved")),
        to_int(raw.get("penalties_missed")),
        to_int(raw.get("yellow_cards")),
        to_int(raw.get("red_cards")),
        to_int(raw.get("saves")),
        to_int(raw.get("bonus")),
        to_int(raw.get("bps")),
        to_decimal(raw.get("influence")),
        to_decimal(raw.get("creativity")),
        to_decimal(raw.get("threat")),
        to_decimal(raw.get("ict_index")),
        to_int(raw.get("clearances_blocks_interceptions")),
        to_int(raw.get("recoveries")),
        to_int(raw.get("tackles")),
        to_int(raw.get("defensive_contribution")),
        to_decimal(raw.get("expected_goals")),
        to_decimal(raw.get("expected_assists")),
        to_decimal(raw.get("expected_goal_involvements")),
        to_decimal(raw.get("expected_goals_conceded")),
        to_int(raw.get("transfers_in")),
        to_int(raw.get("transfers_out")),
        to_int(raw.get("transfers_in_event")),
        to_int(raw.get("transfers_out_event")),
    )


FIXTURE_COLUMNS = (
    "id",
    "code",
    "gameweek_id",
    "team_h_id",
    "team_a_id",
    "team_h_score",
    "team_a_score",
    "team_h_difficulty",
    "team_a_difficulty",
    "kickoff_time",
    "finished",
    "started",
    "minutes",
    "provisional_start_time",
)


def transform_fixture(raw: dict) -> tuple:
    return (
        raw["id"],
        to_int(raw.get("code")),
        to_int(raw.get("event")),
        raw["team_h"],
        raw["team_a"],
        to_int(raw.get("team_h_score")),
        to_int(raw.get("team_a_score")),
        to_int(raw.get("team_h_difficulty")),
        to_int(raw.get("team_a_difficulty")),
        raw.get("kickoff_time"),
        bool(raw.get("finished")),
        bool(raw.get("started")),
        to_int(raw.get("minutes")),
        bool(raw.get("provisional_start_time")),
    )


PLAYER_GAMEWEEK_STATS_COLUMNS = (
    "player_id",
    "fixture_id",
    "gameweek_id",
    "opponent_team_id",
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
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "value",
    "selected",
    "transfers_balance",
    "transfers_in",
    "transfers_out",
    "team_h_score",
    "team_a_score",
    "kickoff_time",
)


def transform_player_gameweek_stat(raw: dict) -> tuple:
    """`raw` is one entry from element-summary/{id}'s "history" list."""
    return (
        raw["element"],
        raw["fixture"],
        raw["round"],
        to_int(raw.get("opponent_team")),
        to_bool(raw.get("was_home")),
        to_int(raw.get("total_points")),
        to_int(raw.get("minutes")),
        to_int(raw.get("starts")),
        to_int(raw.get("goals_scored")),
        to_int(raw.get("assists")),
        to_int(raw.get("clean_sheets")),
        to_int(raw.get("goals_conceded")),
        to_int(raw.get("own_goals")),
        to_int(raw.get("penalties_saved")),
        to_int(raw.get("penalties_missed")),
        to_int(raw.get("yellow_cards")),
        to_int(raw.get("red_cards")),
        to_int(raw.get("saves")),
        to_int(raw.get("bonus")),
        to_int(raw.get("bps")),
        to_decimal(raw.get("influence")),
        to_decimal(raw.get("creativity")),
        to_decimal(raw.get("threat")),
        to_decimal(raw.get("ict_index")),
        to_int(raw.get("clearances_blocks_interceptions")),
        to_int(raw.get("recoveries")),
        to_int(raw.get("tackles")),
        to_int(raw.get("defensive_contribution")),
        to_decimal(raw.get("expected_goals")),
        to_decimal(raw.get("expected_assists")),
        to_decimal(raw.get("expected_goal_involvements")),
        to_decimal(raw.get("expected_goals_conceded")),
        to_int(raw.get("value")),
        to_int(raw.get("selected")),
        to_int(raw.get("transfers_balance")),
        to_int(raw.get("transfers_in")),
        to_int(raw.get("transfers_out")),
        to_int(raw.get("team_h_score")),
        to_int(raw.get("team_a_score")),
        raw.get("kickoff_time"),
    )
