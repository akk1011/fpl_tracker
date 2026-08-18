"""Helpers for resolving Understat's own identifiers to FPL's stable `code`.

Two separate resolution paths, since the data only supports two different
things (verified directly this session, not assumed):

1. Player identity: Understat's understat_id -> that season's FPL element id
   -> player_code. The middle hop only exists for the 2 seasons vaastav also
   ships an id_dict.csv for (2021-22, 2022-23) — confirmed by checking every
   season's HTTP status directly, not "2021-22 onward" as first assumed.
2. Team identity: Understat's team-name string (used in its filenames, e.g.
   "Manchester_United") doesn't match FPL's own name/short_name fields (e.g.
   "Man Utd") — resolved via a small hand-curated map instead.
"""
from __future__ import annotations


def build_understat_to_season_element_map(id_dict_rows: list[dict]) -> dict[int, int]:
    """id_dict.csv -> {understat_id: season_element_id}.

    Only call this for seasons where fetch_csv returned rows for id_dict.csv
    (2021-22, 2022-23 confirmed) — callers must check for None themselves.
    """
    mapping: dict[int, int] = {}
    for row in id_dict_rows:
        try:
            understat_id = int(row["Understat_ID"])
            fpl_id = int(row["FPL_ID"])
        except (KeyError, ValueError, TypeError):
            continue
        mapping[understat_id] = fpl_id
    return mapping


def resolve_team_code(understat_filename_team_name: str, name_map: dict[str, int]) -> int | None:
    """`understat_filename_team_name` is the part of understat_<Name>.csv between
    the prefix and .csv, e.g. "Manchester_United" (underscores, not spaces —
    confirmed against real filenames this session)."""
    return name_map.get(understat_filename_team_name)
