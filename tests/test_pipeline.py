from etl.pipeline import to_int_minutes


def test_to_int_minutes_zero_and_none():
    assert to_int_minutes({"minutes": 0}) == 0
    assert to_int_minutes({}) == 0
    assert to_int_minutes({"minutes": None}) == 0


def test_to_int_minutes_positive_and_string():
    assert to_int_minutes({"minutes": 90}) == 90
    assert to_int_minutes({"minutes": "90"}) == 90
