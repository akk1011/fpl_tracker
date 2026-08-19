"""Unit tests for app/scoring.py.

Boundary tests use clean synthetic inputs (isolating one rule at a time).
The reconciliation tests use real rows fetched live from the 2025-26
merged_gw.csv this session — proving the formula matches FPL's actual
recorded total_points, not just "looks reasonable."
"""
from app.scoring import compute_points_breakdown, sum_breakdowns


def _row(**overrides) -> dict:
    base = {
        "minutes": 0, "goals_scored": 0, "assists": 0, "clean_sheets": 0,
        "goals_conceded": 0, "own_goals": 0, "penalties_saved": 0,
        "penalties_missed": 0, "yellow_cards": 0, "red_cards": 0,
        "saves": 0, "bonus": 0, "defensive_contribution": 0,
    }
    base.update(overrides)
    return base


# --- appearance points ---


def test_appearance_points_boundaries():
    assert compute_points_breakdown(_row(minutes=0), "MID")["appearance"] == 0
    assert compute_points_breakdown(_row(minutes=1), "MID")["appearance"] == 1
    assert compute_points_breakdown(_row(minutes=59), "MID")["appearance"] == 1
    assert compute_points_breakdown(_row(minutes=60), "MID")["appearance"] == 2
    assert compute_points_breakdown(_row(minutes=90), "MID")["appearance"] == 2


# --- position-dependent goal/clean-sheet points ---


def test_goal_points_by_position():
    row = _row(goals_scored=1)
    assert compute_points_breakdown(row, "GKP")["goals"] == 6
    assert compute_points_breakdown(row, "DEF")["goals"] == 6
    assert compute_points_breakdown(row, "MID")["goals"] == 5
    assert compute_points_breakdown(row, "FWD")["goals"] == 4


def test_clean_sheet_points_by_position():
    row = _row(clean_sheets=1)
    assert compute_points_breakdown(row, "GKP")["clean_sheets"] == 4
    assert compute_points_breakdown(row, "DEF")["clean_sheets"] == 4
    assert compute_points_breakdown(row, "MID")["clean_sheets"] == 1
    assert compute_points_breakdown(row, "FWD")["clean_sheets"] == 0


def test_assist_points_flat_across_positions():
    row = _row(assists=2)
    for position in ("GKP", "DEF", "MID", "FWD"):
        assert compute_points_breakdown(row, position)["assists"] == 6


# --- goalkeeper-specific rules ---


def test_saves_points_only_for_goalkeeper():
    row = _row(saves=7)  # 7 // 3 = 2
    assert compute_points_breakdown(row, "GKP")["saves"] == 2
    assert compute_points_breakdown(row, "DEF")["saves"] == 0


def test_penalty_save_and_miss():
    row = _row(penalties_saved=1, penalties_missed=1)
    breakdown = compute_points_breakdown(row, "GKP")
    assert breakdown["penalty_saves"] == 5
    assert breakdown["penalty_misses"] == -2


# --- goals-conceded deduction: GKP/DEF only ---


def test_goals_conceded_penalty_only_for_gkp_def():
    row = _row(goals_conceded=3)  # 3 // 2 = 1 deduction
    assert compute_points_breakdown(row, "GKP")["goals_conceded_penalty"] == -1
    assert compute_points_breakdown(row, "DEF")["goals_conceded_penalty"] == -1
    assert compute_points_breakdown(row, "MID")["goals_conceded_penalty"] == 0
    assert compute_points_breakdown(row, "FWD")["goals_conceded_penalty"] == 0


# --- cards and own goals ---


def test_cards_and_own_goals():
    row = _row(yellow_cards=1, red_cards=1, own_goals=1)
    breakdown = compute_points_breakdown(row, "MID")
    assert breakdown["cards"] == -1 + -3
    assert breakdown["own_goals"] == -2


# --- DEFCON: the rule CLAUDE.md explicitly calls out for threshold tests ---


def test_defcon_def_threshold_boundary():
    assert compute_points_breakdown(_row(defensive_contribution=9), "DEF")["defcon"] == 0
    assert compute_points_breakdown(_row(defensive_contribution=10), "DEF")["defcon"] == 2


def test_defcon_mid_fwd_threshold_boundary():
    assert compute_points_breakdown(_row(defensive_contribution=11), "MID")["defcon"] == 0
    assert compute_points_breakdown(_row(defensive_contribution=12), "MID")["defcon"] == 2
    assert compute_points_breakdown(_row(defensive_contribution=11), "FWD")["defcon"] == 0
    assert compute_points_breakdown(_row(defensive_contribution=12), "FWD")["defcon"] == 2


def test_defcon_capped_at_two_regardless_of_volume():
    assert compute_points_breakdown(_row(defensive_contribution=50), "DEF")["defcon"] == 2
    assert compute_points_breakdown(_row(defensive_contribution=200), "MID")["defcon"] == 2


def test_defcon_goalkeeper_never_eligible():
    """Even with a huge defensive_contribution, a GKP never gets DEFCON points."""
    assert compute_points_breakdown(_row(defensive_contribution=50), "GKP")["defcon"] == 0


def test_defcon_none_defensive_contribution_handled_safely():
    """Older seasons / rows with no DEFCON data (defensive_contribution=None)
    must not crash — should just contribute 0, not raise."""
    row = _row(defensive_contribution=None)
    assert compute_points_breakdown(row, "DEF")["defcon"] == 0


# --- reconciliation against real recorded total_points ---
# Both rows below are real, fetched live from vaastav's 2025-26 merged_gw.csv
# this session — not invented. This is the strongest correctness check: the
# formula must reproduce FPL's actual recorded scoring, not just "look right."


def test_reconciles_real_salah_gw1_2025_26():
    """Mohamed Salah, MID, GW1 2025-26: 1 goal, no DEFCON (defensive_contribution=10 < 12), recorded total_points=8."""
    row = _row(
        minutes=90, goals_scored=1, assists=0, clean_sheets=0,
        goals_conceded=2, bonus=1, defensive_contribution=10,
    )
    breakdown = compute_points_breakdown(row, "MID")
    assert breakdown["total"] == 8


def test_reconciles_real_defender_defcon_gw1_2025_26():
    """Rayan Aït-Nouri, DEF, GW1 2025-26: clean sheet + DEFCON triggered (defensive_contribution=15 >= 10), recorded total_points=9."""
    row = _row(
        minutes=90, goals_scored=0, assists=0, clean_sheets=1,
        goals_conceded=0, bonus=1, defensive_contribution=15,
    )
    breakdown = compute_points_breakdown(row, "DEF")
    assert breakdown["defcon"] == 2
    assert breakdown["total"] == 9


def test_sum_breakdowns_across_two_real_matches():
    """Both the Salah and defender rows above, summed — total must equal
    the sum of their individually-correct totals (8 + 9 = 17), and every
    category must add up too, not just the total."""
    salah = compute_points_breakdown(
        _row(minutes=90, goals_scored=1, goals_conceded=2, bonus=1, defensive_contribution=10),
        "MID",
    )
    defender = compute_points_breakdown(
        _row(minutes=90, clean_sheets=1, goals_conceded=0, bonus=1, defensive_contribution=15),
        "DEF",
    )
    summed = sum_breakdowns([salah, defender])
    assert summed["total"] == 17
    assert summed["appearance"] == 4  # 2 + 2
    assert summed["defcon"] == 2  # 0 (Salah, below threshold) + 2 (defender)


def test_sum_breakdowns_empty_list_is_all_zero():
    summed = sum_breakdowns([])
    assert summed["total"] == 0
    assert all(v == 0 for v in summed.values())


def test_season_aggregate_misuse_gives_wrong_appearance_points():
    """Documents the exact bug this module used to have: passing a
    season-aggregate row (e.g. total season minutes, not one match's
    minutes) through compute_points_breakdown silently gives a wrong
    answer — 2953 minutes resolves to a single 0/1/2 bucket, not ~2 points
    per match actually played. This test exists so nobody re-introduces
    the "season aggregates work the same" assumption without noticing."""
    fake_season_aggregate_row = _row(minutes=2953, goals_scored=27, assists=8)
    breakdown = compute_points_breakdown(fake_season_aggregate_row, "FWD")
    # A real player with these season totals actually scored 239 points
    # (Erling Haaland, 2026-27 preseason carryover, verified live this
    # session) — this function, misused this way, comes nowhere close.
    assert breakdown["total"] != 239
    assert breakdown["appearance"] == 2  # the bug: always capped at 2, never scales with matches played
