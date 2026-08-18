# FPL Analytics Platform

A public, hosted Fantasy Premier League analytics tool — player/team underlying
metrics, points projections (including DEFCON), transfer decision support,
synergy/injury-impact analysis, a mini-league Monte Carlo simulator, and a
chatbot layer on top. Built and run at $0/month.

Full project vision and phase-by-phase plan: [`FPL_Tracker_Spec.md`](FPL_Tracker_Spec.md).
Working rules for whoever (human or agent) is building this: [`CLAUDE.md`](CLAUDE.md).

## Status: Phase 1 — Data foundation

The ETL pulls the official FPL API (`bootstrap-static`, `fixtures`,
`element-summary`) into Postgres. It's designed to run as a scheduled
GitHub Actions job, not a long-running process — see
[`.github/workflows/etl.yml`](.github/workflows/etl.yml) (daily at 06:00 UTC).

### Schema

See [`db/schema.sql`](db/schema.sql). Applied idempotently — the pipeline runs
it (`CREATE TABLE IF NOT EXISTS` etc.) at the start of every ETL run, so
there's no separate migration step.

| Table | What it holds |
|---|---|
| `positions` | GKP/DEF/MID/FWD reference data |
| `teams` | The 20 PL clubs, incl. FPL's strength ratings |
| `gameweeks` | The 38 gameweeks (FPL "events"): deadlines, status |
| `players` | Current-snapshot per-player data: price, form, season totals, DEFCON stats, xG/xA/xGI/xGC |
| `fixtures` | All fixtures for the season, incl. FDR |
| `player_gameweek_stats` | One row per player per fixture played — the core fact table projections/synergy analysis will read from |
| `raw_snapshots` | Raw JSON of the two whole-season endpoints, kept for audit/reprocessing |
| `etl_runs` | Log of each ETL run (status, row counts) |

### Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then fill in DATABASE_URL from your Neon project
python -m etl.pipeline
```

Run just `python -m etl.pipeline --schema-only` to apply the schema without
fetching/loading data.

### Tests

```bash
python -m pytest tests/ -v
```

Runs automatically on every push/PR via
[`.github/workflows/tests.yml`](.github/workflows/tests.yml).

### GitHub Actions setup (once the Neon DB exists)

Add the connection string as a repo secret: **Settings → Secrets and
variables → Actions → New repository secret**, name `DATABASE_URL`. The
nightly job (and `workflow_dispatch` for manual runs) will pick it up
automatically.
