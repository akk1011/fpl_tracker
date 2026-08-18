"""Fetches CSV files from vaastav/Fantasy-Premier-League's raw GitHub content.

Not every file exists for every season — confirmed directly this session:
teams.csv/understat/ start at 2019-20, id_dict.csv exists only for 2021-22
and 2022-23, understat/ is absent again for 2025-26. Callers must expect
`fetch_csv` to return None for a missing file and handle it, not treat a
404 as an error.
"""
from __future__ import annotations

import csv
import io
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl.config import REQUEST_HEADERS, REQUEST_MAX_RETRIES, REQUEST_TIMEOUT_SECONDS

log = logging.getLogger(__name__)

RAW_BASE = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    retry = Retry(
        total=REQUEST_MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _make_session()


def fetch_csv(season: str, relative_path: str) -> list[dict] | None:
    """Fetch one CSV file for a season and parse it into a list of dicts.

    Returns None if the file doesn't exist for that season (a real,
    expected case — not every file exists every year). Raises for any
    other HTTP error (after the session's built-in retries are exhausted).

    Field names are stripped of surrounding whitespace — id_dict.csv's
    header has been confirmed to contain a leading space after each comma
    (e.g. "Understat_ID, FPL_ID, ..."), which csv.DictReader would
    otherwise turn into literal ' FPL_ID' keys.
    """
    url = f"{RAW_BASE}/{season}/{relative_path}"
    resp = _session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    text = resp.content.decode("utf-8-sig")  # some files ship a BOM
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
    # id_dict.csv's real header (and its data rows) use ", " as the
    # separator, not just ",": both keys AND values need stripping, or
    # values like FPL_ID come through as " 233" instead of "233".
    rows = [
        {
            (k.strip() if k else k): (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
        }
        for row in reader
    ]
    log.info("Fetched %s/%s: %d rows", season, relative_path, len(rows))
    return rows


def fetch_understat_team_file(season: str, team_name: str) -> list[dict] | None:
    """Understat team-match files are named after the team, e.g. understat_Arsenal.csv."""
    return fetch_csv(season, f"understat/understat_{team_name}.csv")
