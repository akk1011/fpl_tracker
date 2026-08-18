"""Configuration loaded from environment variables (or a local .env for dev).

Nothing paid or account-specific lives in code — everything comes from env
vars so the same code runs locally and in the GitHub Actions cron job (where
DATABASE_URL is injected from a repo secret).
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

# Loads .env if present; a no-op in CI where real env vars are already set.
load_dotenv()

FPL_API_BASE = "https://fantasy.premierleague.com/api"

# FPL's API rejects requests with no User-Agent / a bare Python default one.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; fpl-analytics-etl/1.0; "
        "+https://github.com/akk1011/fpl_tracker)"
    )
}

DATABASE_URL = os.environ.get("DATABASE_URL")

# How many concurrent element-summary requests to run. FPL's API has no
# documented rate limit, but this is a public/free endpoint being hit by a
# public/free project — stay polite rather than fast.
ELEMENT_SUMMARY_MAX_WORKERS = int(os.environ.get("ELEMENT_SUMMARY_MAX_WORKERS", "5"))

REQUEST_TIMEOUT_SECONDS = 15
REQUEST_MAX_RETRIES = 3


def require_database_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env locally, or "
            "set the DATABASE_URL secret in the GitHub repo (Settings > "
            "Secrets and variables > Actions) for the scheduled job."
        )
    return DATABASE_URL
