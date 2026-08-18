"""Unit tests for etl/historical/transform.py.

Sample dicts below are real rows fetched live from vaastav's repo during
this session (2025-26 = the pilot season; understat/id_dict samples are
from 2024-25/2021-22 since 2025-26 has neither) — not invented shapes.
"""
from decimal import Decimal

from etl.historical import transform

# A real players_raw.csv row: Mohamed Salah, 2025-26 (mid-season snapshot).
SALAH_PLAYERS_RAW_2025_26 = {
    "assists": "7", "bonus": "11", "bps": "392", "clean_sheets": "7",
    "clearances_blocks_interceptions": "11", "code": "118748",
    "cost_change_start": "-5", "creativity": "740.7",
    "defensive_contribution": "109", "element_type": "3",
    "expected_assists": "5.44", "expected_goal_involvements": "13.67",
    "expected_goals": "8.23", "expected_goals_conceded": "30.94",
    "first_name": "Mohamed", "goals_conceded": "35", "goals_scored": "7",
    "ict_index": "207.1", "id": "381", "influence": "524.8", "minutes": "2144",
    "now_cost": "140", "own_goals": "0", "penalties_missed": "0",
    "penalties_saved": "0", "recoveries": "81", "red_cards": "0",
    "saves": "0", "second_name": "Salah", "starts": "23", "tackles": "17",
    "team": "12", "team_code": "14", "threat": "805.0", "total_points": "123",
    "web_name": "M.Salah", "yellow_cards": "1",
}

# A real merged_gw.csv row: Salah, 2025-26, GW1.
SALAH_MERGED_GW_2025_26_GW1 = {
    "assists": "0", "bonus": "1", "bps": "36", "clean_sheets": "0",
    "clearances_blocks_interceptions": "1", "creativity": "33.8",
    "defensive_contribution": "10", "element": "381",
    "expected_assists": "0.11", "expected_goal_involvements": "0.37",
    "expected_goals": "0.26", "expected_goals_conceded": "1.70",
    "fixture": "1", "goals_conceded": "2", "goals_scored": "1",
    "ict_index": "13.4", "influence": "49.0",
    "kickoff_time": "2025-08-15T19:00:00Z", "minutes": "90",
    "opponent_team": "4", "own_goals": "0", "penalties_missed": "0",
    "penalties_saved": "0", "recoveries": "9", "red_cards": "0", "round": "1",
    "saves": "0", "selected": "5221323", "starts": "1", "tackles": "0",
    "team_a_score": "2", "team_h_score": "4", "threat": "51.0",
    "total_points": "8", "transfers_balance": "0", "transfers_in": "0",
    "transfers_out": "0", "value": "145", "was_home": "True",
    "yellow_cards": "0",
}

# A real teams.csv row: Arsenal, 2025-26.
ARSENAL_TEAMS_2025_26 = {
    "code": "3", "id": "1", "name": "Arsenal", "short_name": "ARS",
    "strength": "5", "strength_overall_home": "1305",
    "strength_overall_away": "1355", "strength_attack_home": "1340",
    "strength_attack_away": "1390", "strength_defence_home": "1270",
    "strength_defence_away": "1320",
}

# A real understat/understat_player.csv row (2024-25 — 2025-26 has none).
SALAH_UNDERSTAT_2024_25 = {
    "id": "1250", "player_name": "Mohamed Salah", "games": "31",
    "time": "2766", "goals": "27", "xG": "22.73575109243393", "assists": "17",
    "xA": "11.92607805505395", "shots": "108", "key_passes": "70",
    "team_title": "Liverpool", "npg": "18", "npxG": "15.885231513530016",
    "xGChain": "36.5840120986104", "xGBuildup": "11.152481760829687",
}

# A real understat_<Team>.csv row (2020-21 Arsenal, home fixture).
ARSENAL_UNDERSTAT_TEAM_2020_21 = {
    "h_a": "h", "xG": "1.32902", "xGA": "2.06377", "npxG": "1.32902",
    "npxGA": "2.06377", "deep": "16", "deep_allowed": "4", "scored": "2",
    "missed": "1", "xpts": "0.8155", "result": "w",
    "date": "2020-09-19 19:00:00",
}


def test_is_defcon_recorded_boundary():
    assert transform.is_defcon_recorded("2025-26") is True
    assert transform.is_defcon_recorded("2024-25") is False
    assert transform.is_defcon_recorded("2016-17") is False


def test_to_int_handles_float_style_strings():
    """Some historical CSVs have '0.0'-style ints, unlike the live API."""
    assert transform.to_int("0.0") == 0
    assert transform.to_int("90") == 90
    assert transform.to_int("") is None


def test_to_bool_handles_string_true_false():
    assert transform.to_bool("True") is True
    assert transform.to_bool("False") is False
    assert transform.to_bool("") is None


def test_transform_historical_team_matches_column_count():
    row = transform.transform_historical_team(ARSENAL_TEAMS_2025_26, "2025-26")
    assert len(row) == len(transform.HISTORICAL_TEAM_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_TEAM_COLUMNS, row))
    assert as_dict["season"] == "2025-26"
    assert as_dict["team_code"] == 3
    assert as_dict["season_team_id"] == 1
    assert as_dict["name"] == "Arsenal"


def test_transform_historical_team_minimal_matches_column_count():
    row = transform.transform_historical_team_minimal("2016-17", 3, 1)
    assert len(row) == len(transform.HISTORICAL_TEAM_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_TEAM_COLUMNS, row))
    assert as_dict["team_code"] == 3
    assert as_dict["name"] is None  # honestly null, not guessed


def test_transform_historical_player_matches_column_count_and_key_fields():
    row = transform.transform_historical_player(SALAH_PLAYERS_RAW_2025_26, "2025-26")
    assert len(row) == len(transform.HISTORICAL_PLAYER_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_PLAYER_COLUMNS, row))

    assert as_dict["player_code"] == 118748
    assert as_dict["season_element_id"] == 381
    assert as_dict["team_code"] == 14
    assert as_dict["position"] == "MID"
    assert as_dict["web_name"] == "M.Salah"
    assert as_dict["end_cost"] == 140
    assert as_dict["start_cost"] == 145  # now_cost(140) - cost_change_start(-5)
    assert as_dict["defensive_contribution"] == 109
    assert as_dict["defcon_recorded"] is True  # 2025-26: real recorded DEFCON
    assert as_dict["expected_goals"] == Decimal("8.23")


def test_transform_historical_player_defcon_not_recorded_pre_2025_26():
    row = transform.transform_historical_player(SALAH_PLAYERS_RAW_2025_26, "2024-25")
    as_dict = dict(zip(transform.HISTORICAL_PLAYER_COLUMNS, row))
    assert as_dict["defcon_recorded"] is False


def test_transform_historical_player_gameweek_stat_matches_column_count():
    row = transform.transform_historical_player_gameweek_stat(
        SALAH_MERGED_GW_2025_26_GW1, "2025-26", player_code=118748, opponent_team_code=4,
    )
    assert len(row) == len(transform.HISTORICAL_PLAYER_GAMEWEEK_STATS_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_PLAYER_GAMEWEEK_STATS_COLUMNS, row))

    assert as_dict["player_code"] == 118748
    assert as_dict["fixture_season_id"] == 1
    assert as_dict["round"] == 1
    assert as_dict["opponent_team_code"] == 4
    assert as_dict["was_home"] is True
    assert as_dict["total_points"] == 8
    assert as_dict["defensive_contribution"] == 10
    assert as_dict["defcon_recorded"] is True


def test_transform_historical_understat_player_stat_matches_column_count():
    row = transform.transform_historical_understat_player_stat(
        SALAH_UNDERSTAT_2024_25, "2024-25", player_code=118748,
    )
    assert len(row) == len(transform.HISTORICAL_UNDERSTAT_PLAYER_STATS_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_UNDERSTAT_PLAYER_STATS_COLUMNS, row))
    assert as_dict["understat_id"] == 1250
    assert as_dict["player_code"] == 118748
    assert as_dict["goals"] == 27
    assert as_dict["xg"] == Decimal("22.73575109243393")


def test_transform_historical_understat_player_stat_unlinked_when_no_id_dict():
    """player_code is None outside the 2 seasons with id_dict.csv — stored, not dropped."""
    row = transform.transform_historical_understat_player_stat(
        SALAH_UNDERSTAT_2024_25, "2024-25", player_code=None,
    )
    as_dict = dict(zip(transform.HISTORICAL_UNDERSTAT_PLAYER_STATS_COLUMNS, row))
    assert as_dict["player_code"] is None
    assert as_dict["player_name"] == "Mohamed Salah"  # name kept even when unlinked


def test_transform_historical_understat_team_stat_matches_column_count():
    row = transform.transform_historical_understat_team_stat(
        ARSENAL_UNDERSTAT_TEAM_2020_21, "2020-21", team_code=3,
    )
    assert len(row) == len(transform.HISTORICAL_UNDERSTAT_TEAM_STATS_COLUMNS)
    as_dict = dict(zip(transform.HISTORICAL_UNDERSTAT_TEAM_STATS_COLUMNS, row))
    assert as_dict["team_code"] == 3
    assert as_dict["was_home"] is True
    assert as_dict["xg"] == Decimal("1.32902")
    assert as_dict["result"] == "w"
