"""Integration test fixtures: seed a real Postgres (via the existing live
ETL) and hit real FastAPI endpoints against it — not mocks.

Requires DATABASE_URL to already point at a running (throwaway) Postgres
before pytest starts — locally that's the same Docker pattern used
throughout Phase 1; in CI it's a `services: postgres:` container (see
.github/workflows/tests.yml). Seeding reuses etl/pipeline.py directly via
subprocess against the repo-root venv, rather than importing etl/ into
backend/'s own dependency graph — these are two independently-deployed
projects (see the Phase 2 plan) and shouldn't share import-time coupling.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROOT_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


@pytest.fixture(scope="session")
def seeded_database():
    """NOT autouse — only tests that actually need a DB should pull this in
    (via the `client` fixture below). Making this autouse was a real bug
    caught during Phase 2 testing: it skipped every test in the session,
    including pure-logic tests (test_scoring.py) that never touch a
    database at all, whenever DATABASE_URL wasn't set."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip(
            "DATABASE_URL not set — integration tests need a running "
            "throwaway Postgres. See backend/tests/conftest.py."
        )

    python = str(ROOT_VENV_PYTHON) if ROOT_VENV_PYTHON.exists() else sys.executable
    result = subprocess.run(
        [python, "-m", "etl.pipeline"],
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(f"Seeding live ETL failed:\n{result.stdout}\n{result.stderr}")

    return database_url


@pytest.fixture
def client(seeded_database):
    # Imported here (not at module scope) so DATABASE_URL is set before
    # app.db is first touched by any request.
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
