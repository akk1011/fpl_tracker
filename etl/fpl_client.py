"""Thin client for the official FPL API.

Kept deliberately dumb: no caching, no business logic, just HTTP + retries.
Must only ever be called server-side (this module, the GitHub Actions job) —
the official API is CORS-blocked, so the frontend/backend serverless
functions read from Postgres instead, never from here directly.
"""
from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl.config import (
    FPL_API_BASE,
    REQUEST_HEADERS,
    REQUEST_MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
)

log = logging.getLogger(__name__)


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


def _get(path: str, params: dict | None = None) -> dict | list:
    url = f"{FPL_API_BASE}{path}"
    resp = _session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()


def get_bootstrap_static() -> dict:
    """Players, teams, gameweeks (events), positions — the season-wide snapshot."""
    return _get("/bootstrap-static/")


def get_fixtures(event: int | None = None) -> list:
    """All fixtures, or just one gameweek's if `event` is given."""
    params = {"event": event} if event is not None else None
    return _get("/fixtures/", params=params)


def get_element_summary(player_id: int) -> dict:
    """Per-player match history + upcoming fixtures + past-seasons summary."""
    return _get(f"/element-summary/{player_id}/")
