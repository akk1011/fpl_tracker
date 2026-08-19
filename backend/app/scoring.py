"""Pure logic: real FPL scoring rules applied to already-recorded stats.

This is deliberately backward-looking and deterministic — "these actual
recorded stats produced these actual points" — not a projection/xP model
(that's Phase 3's job). No DB, no framework, fully unit-testable.

Rules encoded here are the standard FPL rules (2025/26 -> 2026/27, per spec
§3, "confirmed unchanged") plus DEFCON. `bonus` is NOT recomputed — it's
BPS-derived from comparing every player in a match, which needs full
match-level data this module doesn't have; it's passed through from the
already-recorded `bonus` column, same as the official API does.

DEFCON note: FPL's own `defensive_contribution` field turns out to already
be the correct position-dependent combined count — verified directly against
two real players' 2025-26 rows this session: for a DEF (Gabriel),
defensive_contribution (277) == clearances_blocks_interceptions (239) +
tackles (38), recoveries NOT included. For a MID (Salah), defensive_
contribution (109) == clearances_blocks_interceptions (11) + tackles (17) +
recoveries (81), recoveries INCLUDED. That's exactly DEF's "10+ CBIT" vs
MID/FWD's "12+ CBIRT" from spec §3 — FPL has already done the position-
dependent combination, so this module thresholds that field directly rather
than re-deriving CBIT/CBIRT from the raw components itself.
"""
from __future__ import annotations

from typing import TypedDict

Position = str  # "GKP" | "DEF" | "MID" | "FWD"

GOAL_POINTS = {"GKP": 6, "DEF": 6, "MID": 5, "FWD": 4}
CLEAN_SHEET_POINTS = {"GKP": 4, "DEF": 4, "MID": 1, "FWD": 0}
ASSIST_POINTS = 3
SAVES_PER_POINT = 3
PENALTY_SAVE_POINTS = 5
PENALTY_MISS_POINTS = -2
GOALS_CONCEDED_PER_DEDUCTION = 2  # GKP/DEF only
YELLOW_CARD_POINTS = -1
RED_CARD_POINTS = -3
OWN_GOAL_POINTS = -2
DEFCON_POINTS = 2
DEFCON_THRESHOLD = {"DEF": 10, "MID": 12, "FWD": 12}  # GKP: not eligible


class PointsBreakdown(TypedDict):
    appearance: int
    goals: int
    assists: int
    clean_sheets: int
    goals_conceded_penalty: int
    saves: int
    penalty_saves: int
    penalty_misses: int
    cards: int
    own_goals: int
    defcon: int
    bonus: int
    total: int


def _appearance_points(minutes: int) -> int:
    if minutes >= 60:
        return 2
    if minutes >= 1:
        return 1
    return 0


def _defcon_points(position: Position, defensive_contribution: int | None) -> int:
    if position == "GKP" or defensive_contribution is None:
        return 0
    threshold = DEFCON_THRESHOLD.get(position)
    if threshold is None:
        return 0
    return DEFCON_POINTS if defensive_contribution >= threshold else 0


def compute_points_breakdown(row: dict, position: Position) -> PointsBreakdown:
    """`row` MUST be a single-match row (player_gameweek_stats-shaped) —
    NOT a season-aggregate `players` row. The arithmetic does not distribute
    over a season total: `appearance` treats `minutes` as one match's tally
    (season minutes like 2953 would wrongly resolve to a single 0/1/2
    instead of 2-points-per-match-played), and both `saves // 3` and
    `goals_conceded // 2` don't distribute over a sum the way multiplication
    does (2+2 saves across two matches = 0+0 points; 4 saves in one bucket =
    1 point — different results for the same underlying data).

    Caught this directly: an earlier version of this docstring claimed
    season aggregates "worked the same" — a real player's season-aggregate
    breakdown then landed at 175 total vs. their actual recorded
    total_points of 239. For a season-level breakdown, compute this
    function once per real match row and sum with `sum_breakdowns()` below.

    Enforced, not just documented: raises if `row` doesn't look like a
    per-match row. `gameweek_id` is present on every player_gameweek_stats
    row and absent from the season-aggregate `players` row — a hard,
    deterministic discriminator (not a heuristic like "minutes look too
    high"), so this catches the exact bug above at *any* call site, not
    just the one endpoint that happened to have a test for it.
    """
    if "gameweek_id" not in row:
        raise ValueError(
            "compute_points_breakdown() received a row with no 'gameweek_id' "
            "— this looks like a season-aggregate row, not a single match. "
            "See this function's docstring for why that silently gives a "
            "wrong answer. Query player_gameweek_stats and sum with "
            "sum_breakdowns() instead."
        )

    minutes = row.get("minutes") or 0
    goals_scored = row.get("goals_scored") or 0
    assists = row.get("assists") or 0
    clean_sheets = row.get("clean_sheets") or 0
    goals_conceded = row.get("goals_conceded") or 0
    own_goals = row.get("own_goals") or 0
    penalties_saved = row.get("penalties_saved") or 0
    penalties_missed = row.get("penalties_missed") or 0
    yellow_cards = row.get("yellow_cards") or 0
    red_cards = row.get("red_cards") or 0
    saves = row.get("saves") or 0
    bonus = row.get("bonus") or 0
    defensive_contribution = row.get("defensive_contribution")

    appearance = _appearance_points(minutes)
    goals = goals_scored * GOAL_POINTS.get(position, 0)
    assists_pts = assists * ASSIST_POINTS
    clean_sheet_pts = clean_sheets * CLEAN_SHEET_POINTS.get(position, 0)
    saves_pts = saves // SAVES_PER_POINT if position == "GKP" else 0
    penalty_save_pts = penalties_saved * PENALTY_SAVE_POINTS
    penalty_miss_pts = penalties_missed * PENALTY_MISS_POINTS
    cards_pts = yellow_cards * YELLOW_CARD_POINTS + red_cards * RED_CARD_POINTS
    own_goal_pts = own_goals * OWN_GOAL_POINTS
    defcon_pts = _defcon_points(position, defensive_contribution)

    goals_conceded_penalty = 0
    if position in ("GKP", "DEF"):
        goals_conceded_penalty = -(goals_conceded // GOALS_CONCEDED_PER_DEDUCTION)

    total = (
        appearance + goals + assists_pts + clean_sheet_pts + goals_conceded_penalty
        + saves_pts + penalty_save_pts + penalty_miss_pts + cards_pts + own_goal_pts
        + defcon_pts + bonus
    )

    return PointsBreakdown(
        appearance=appearance,
        goals=goals,
        assists=assists_pts,
        clean_sheets=clean_sheet_pts,
        goals_conceded_penalty=goals_conceded_penalty,
        saves=saves_pts,
        penalty_saves=penalty_save_pts,
        penalty_misses=penalty_miss_pts,
        cards=cards_pts,
        own_goals=own_goal_pts,
        defcon=defcon_pts,
        bonus=bonus,
        total=total,
    )


_BREAKDOWN_KEYS = (
    "appearance", "goals", "assists", "clean_sheets", "goals_conceded_penalty",
    "saves", "penalty_saves", "penalty_misses", "cards", "own_goals",
    "defcon", "bonus", "total",
)


def sum_breakdowns(breakdowns: list[PointsBreakdown]) -> PointsBreakdown:
    """Sum several per-match breakdowns into a season/range total. This is
    the only correct way to get a multi-match total from this module — see
    the warning on compute_points_breakdown about why season-aggregate rows
    can't be passed through it directly."""
    totals = {key: 0 for key in _BREAKDOWN_KEYS}
    for breakdown in breakdowns:
        for key in _BREAKDOWN_KEYS:
            totals[key] += breakdown[key]
    return PointsBreakdown(**totals)
