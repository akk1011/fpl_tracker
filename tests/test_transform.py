"""Unit tests for etl/transform.py.

Sample dicts below are trimmed from real live responses pulled from the
official FPL API during development (2026/27 season), not invented shapes.
"""
from decimal import Decimal

from etl import transform

# --- scalar coercion helpers -------------------------------------------------


def test_to_decimal_handles_numeric_string():
    assert transform.to_decimal("4.5") == Decimal("4.5")


def test_to_decimal_handles_none_and_empty_string():
    assert transform.to_decimal(None) is None
    assert transform.to_decimal("") is None


def test_to_decimal_handles_invalid_string():
    assert transform.to_decimal("not-a-number") is None


def test_to_int_handles_none_and_empty_string():
    assert transform.to_int(None) is None
    assert transform.to_int("") is None


def test_to_int_handles_numeric_string_and_int():
    assert transform.to_int("42") == 42
    assert transform.to_int(42) == 42


def test_to_bool_passes_through_and_handles_none():
    assert transform.to_bool(True) is True
    assert transform.to_bool(False) is False
    assert transform.to_bool(None) is None


# --- row transforms: column/value count must always match -------------------


def test_transform_position_matches_column_count():
    raw = {
        "id": 2,
        "plural_name": "Defenders",
        "plural_name_short": "DEF",
        "singular_name": "Defender",
        "singular_name_short": "DEF",
        "squad_min_play": 3,
        "squad_max_play": 5,
    }
    row = transform.transform_position(raw)
    assert len(row) == len(transform.POSITION_COLUMNS)
    assert row[0] == 2
    assert row[1] == "Defender"


def test_transform_team_handles_preseason_zero_strength():
    raw = {
        "id": 1, "code": 3, "name": "Arsenal", "short_name": "ARS",
        "strength": None, "played": 0, "win": 0, "draw": 0, "loss": 0,
        "points": 0, "position": 0,
        "strength_overall_home": 4, "strength_overall_away": 5,
        "strength_attack_home": 0, "strength_attack_away": 0,
        "strength_defence_home": 0, "strength_defence_away": 0,
    }
    row = transform.transform_team(raw)
    assert len(row) == len(transform.TEAM_COLUMNS)
    assert row[0] == 1
    assert row[2] == "Arsenal"
    # strength=None (pre-season) must survive as None, not error/0
    strength_index = transform.TEAM_COLUMNS.index("strength")
    assert row[strength_index] is None


def test_transform_gameweek_matches_column_count():
    raw = {
        "id": 1, "name": "Gameweek 1", "deadline_time": "2026-08-21T17:30:00Z",
        "finished": False, "data_checked": False, "is_previous": False,
        "is_current": False, "is_next": True, "average_entry_score": 0,
        "highest_score": None, "top_element": None, "most_selected": None,
        "most_transferred_in": None, "most_captained": None,
        "most_vice_captained": None, "transfers_made": 0,
    }
    row = transform.transform_gameweek(raw)
    assert len(row) == len(transform.GAMEWEEK_COLUMNS)
    assert row[0] == 1
    assert row[3] is False  # finished
    assert row[7] is True   # is_next


def test_transform_player_matches_column_count_and_key_fields():
    raw = {
        "id": 4, "code": 226597, "team": 1, "element_type": 2,
        "first_name": "Gabriel", "second_name": "dos Santos Magalhães",
        "web_name": "Gabriel", "status": "a", "news": "",
        "chance_of_playing_this_round": None, "chance_of_playing_next_round": None,
        "now_cost": 80, "cost_change_start": 0, "selected_by_percent": "28.6",
        "form": "0.0", "points_per_game": "6.5", "value_season": "26.1",
        "total_points": 209, "event_points": 0, "minutes": 2750, "starts": 30,
        "goals_scored": 3, "assists": 5, "clean_sheets": 18, "goals_conceded": 20,
        "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0,
        "yellow_cards": 4, "red_cards": 0, "saves": 0, "bonus": 30, "bps": 724,
        "influence": "824.0", "creativity": "128.5", "threat": "298.0",
        "ict_index": "125.0", "clearances_blocks_interceptions": 239,
        "recoveries": 64, "tackles": 38, "defensive_contribution": 277,
        "expected_goals": "2.94", "expected_assists": "1.75",
        "expected_goal_involvements": "4.69", "expected_goals_conceded": "22.01",
        "transfers_in": 0, "transfers_out": 0, "transfers_in_event": 0,
        "transfers_out_event": 0,
    }
    row = transform.transform_player(raw)
    assert len(row) == len(transform.PLAYER_COLUMNS)

    as_dict = dict(zip(transform.PLAYER_COLUMNS, row))
    assert as_dict["id"] == 4
    assert as_dict["team_id"] == 1
    assert as_dict["position_id"] == 2
    assert as_dict["web_name"] == "Gabriel"
    assert as_dict["now_cost"] == 80
    assert as_dict["defensive_contribution"] == 277
    assert as_dict["expected_goals"] == Decimal("2.94")
    assert as_dict["selected_by_percent"] == Decimal("28.6")


def test_transform_fixture_matches_column_count_and_nullable_event():
    raw = {
        "id": 1, "code": 2645195, "event": 1, "finished": False,
        "started": False, "team_a": 7, "team_a_score": None,
        "team_h": 1, "team_h_score": None, "minutes": 0,
        "provisional_start_time": False, "kickoff_time": "2026-08-21T19:00:00Z",
        "team_h_difficulty": 2, "team_a_difficulty": 5,
    }
    row = transform.transform_fixture(raw)
    assert len(row) == len(transform.FIXTURE_COLUMNS)
    as_dict = dict(zip(transform.FIXTURE_COLUMNS, row))
    assert as_dict["team_h_id"] == 1
    assert as_dict["team_a_id"] == 7
    assert as_dict["team_h_score"] is None


def test_transform_fixture_handles_unscheduled_fixture_no_event():
    """Some fixtures (e.g. postponed) have event=None — must not raise."""
    raw = {
        "id": 999, "code": 1, "event": None, "finished": False,
        "started": False, "team_a": 2, "team_h": 3, "minutes": 0,
        "provisional_start_time": True,
    }
    row = transform.transform_fixture(raw)
    as_dict = dict(zip(transform.FIXTURE_COLUMNS, row))
    assert as_dict["gameweek_id"] is None


def test_transform_player_gameweek_stat_matches_column_count():
    raw = {
        "element": 4, "fixture": 1, "opponent_team": 7, "total_points": 6,
        "was_home": True, "kickoff_time": "2026-08-21T19:00:00Z",
        "team_h_score": 2, "team_a_score": 0, "round": 1, "minutes": 90,
        "goals_scored": 0, "assists": 0, "clean_sheets": 1, "goals_conceded": 0,
        "own_goals": 0, "penalties_saved": 0, "penalties_missed": 0,
        "yellow_cards": 0, "red_cards": 0, "saves": 0, "bonus": 2, "bps": 30,
        "influence": "35.4", "creativity": "3.0", "threat": "10.0",
        "ict_index": "4.8", "clearances_blocks_interceptions": 9,
        "recoveries": 5, "tackles": 3, "defensive_contribution": 12,
        "starts": 1, "expected_goals": "0.01", "expected_assists": "0.00",
        "expected_goal_involvements": "0.01", "expected_goals_conceded": "0.85",
        "value": 80, "transfers_balance": 0, "selected": 5000000,
        "transfers_in": 0, "transfers_out": 0,
    }
    row = transform.transform_player_gameweek_stat(raw)
    assert len(row) == len(transform.PLAYER_GAMEWEEK_STATS_COLUMNS)
    as_dict = dict(zip(transform.PLAYER_GAMEWEEK_STATS_COLUMNS, row))
    assert as_dict["player_id"] == 4
    assert as_dict["fixture_id"] == 1
    assert as_dict["gameweek_id"] == 1
    assert as_dict["was_home"] is True
    assert as_dict["defensive_contribution"] == 12
