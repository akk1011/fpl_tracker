from etl.historical import understat

# Real id_dict.csv row shape, 2021-22 (header confirmed to have leading
# spaces after each comma — this dict simulates post-strip keys, since
# stripping happens in vaastav_client.fetch_csv before rows reach here).
ID_DICT_ROW = {
    "Understat_ID": "1250", "FPL_ID": "233",
    "Understat_Name": "Mohamed Salah", "FPL_Name": "Mohamed Salah",
}


def test_build_understat_to_season_element_map():
    mapping = understat.build_understat_to_season_element_map([ID_DICT_ROW])
    assert mapping == {1250: 233}


def test_build_understat_to_season_element_map_skips_malformed_rows():
    malformed = {"Understat_ID": "not-a-number", "FPL_ID": "233"}
    mapping = understat.build_understat_to_season_element_map([malformed, ID_DICT_ROW])
    assert mapping == {1250: 233}


def test_resolve_team_code():
    name_map = {"Arsenal": 3, "Manchester_United": 1}
    assert understat.resolve_team_code("Arsenal", name_map) == 3
    assert understat.resolve_team_code("Nonexistent_Club", name_map) is None
