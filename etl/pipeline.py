"""Orchestrates one full ETL run: fetch -> transform -> load.

Entry point for both local runs (`python -m etl.pipeline`) and the nightly
GitHub Actions job. Schema is applied idempotently at the start of every run
so there's no separate migration step to remember.
"""
from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from etl import db, fpl_client, transform

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def load_bootstrap_static(conn, bootstrap: dict) -> tuple[int, int]:
    db.insert_raw_snapshot(conn, "bootstrap_static", bootstrap)

    position_rows = [transform.transform_position(p) for p in bootstrap["element_types"]]
    db.upsert(
        conn, "positions", transform.POSITION_COLUMNS, position_rows,
        conflict_columns=("id",), has_updated_at=False,
    )

    team_rows = [transform.transform_team(t) for t in bootstrap["teams"]]
    teams_upserted = db.upsert(
        conn, "teams", transform.TEAM_COLUMNS, team_rows, conflict_columns=("id",),
    )

    gameweek_rows = [transform.transform_gameweek(g) for g in bootstrap["events"]]
    db.upsert(
        conn, "gameweeks", transform.GAMEWEEK_COLUMNS, gameweek_rows,
        conflict_columns=("id",),
    )

    player_rows = [transform.transform_player(p) for p in bootstrap["elements"]]
    players_upserted = db.upsert(
        conn, "players", transform.PLAYER_COLUMNS, player_rows, conflict_columns=("id",),
    )

    log.info(
        "Loaded bootstrap-static: %d positions, %d teams, %d gameweeks, %d players",
        len(position_rows), teams_upserted, len(gameweek_rows), players_upserted,
    )
    return teams_upserted, players_upserted


def load_fixtures(conn) -> int:
    fixtures = fpl_client.get_fixtures()
    db.insert_raw_snapshot(conn, "fixtures", fixtures)

    fixture_rows = [transform.transform_fixture(f) for f in fixtures]
    fixtures_upserted = db.upsert(
        conn, "fixtures", transform.FIXTURE_COLUMNS, fixture_rows, conflict_columns=("id",),
    )
    log.info("Loaded %d fixtures", fixtures_upserted)
    return fixtures_upserted


def load_player_gameweek_stats(conn, bootstrap: dict, max_workers: int) -> int:
    # Only players with minutes > 0 can have any current-season history rows
    # to fetch. Note: bootstrap-static's `minutes`/`total_points` etc. carry
    # forward the *previous* season's cumulative totals until FPL resets them
    # once GW1 actually kicks off — confirmed live on 2026-08-17, 4 days
    # before this season's GW1 deadline: ~400 of 590 players already showed
    # nonzero minutes, and every element-summary history list was empty. So
    # this filter doesn't skip much pre-season, but keeps cutting fetches to
    # only players who've actually featured once the season is under way.
    candidate_ids = [
        p["id"] for p in bootstrap["elements"] if to_int_minutes(p) > 0
    ]
    if not candidate_ids:
        log.info("No players with minutes yet — skipping element-summary fetch")
        return 0

    all_stat_rows: list[tuple] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fpl_client.get_element_summary, pid): pid for pid in candidate_ids
        }
        for future in as_completed(futures):
            player_id = futures[future]
            try:
                summary = future.result()
            except Exception:
                log.exception("Failed to fetch element-summary for player %d", player_id)
                continue
            for history_entry in summary.get("history", []):
                all_stat_rows.append(transform.transform_player_gameweek_stat(history_entry))

    stats_upserted = db.upsert(
        conn,
        "player_gameweek_stats",
        transform.PLAYER_GAMEWEEK_STATS_COLUMNS,
        all_stat_rows,
        conflict_columns=("player_id", "fixture_id"),
    )
    log.info(
        "Loaded %d player-gameweek stat rows from %d players",
        stats_upserted, len(candidate_ids),
    )
    return stats_upserted


def to_int_minutes(player: dict) -> int:
    minutes = player.get("minutes")
    return int(minutes) if minutes else 0


def run(max_workers: int, schema_only: bool = False) -> None:
    with db.get_connection() as conn:
        db.apply_schema(conn)
        if schema_only:
            log.info("Schema applied. --schema-only set, exiting.")
            return

        run_id = db.start_etl_run(conn)
        try:
            bootstrap = fpl_client.get_bootstrap_static()
            teams_upserted, players_upserted = load_bootstrap_static(conn, bootstrap)
            fixtures_upserted = load_fixtures(conn)
            stats_upserted = load_player_gameweek_stats(conn, bootstrap, max_workers)
        except Exception as exc:
            db.finish_etl_run(conn, run_id, status="failed", detail=str(exc))
            raise
        else:
            db.finish_etl_run(
                conn,
                run_id,
                status="success",
                teams_upserted=teams_upserted,
                players_upserted=players_upserted,
                fixtures_upserted=fixtures_upserted,
                gameweek_stats_upserted=stats_upserted,
            )
            log.info("ETL run %d completed successfully", run_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FPL data ETL pipeline")
    parser.add_argument(
        "--schema-only", action="store_true",
        help="Apply the DB schema and exit, without fetching/loading any data",
    )
    parser.add_argument(
        "--max-workers", type=int, default=None,
        help="Concurrent element-summary requests (default: ELEMENT_SUMMARY_MAX_WORKERS env var, or 5)",
    )
    args = parser.parse_args()

    from etl.config import ELEMENT_SUMMARY_MAX_WORKERS

    max_workers = args.max_workers or ELEMENT_SUMMARY_MAX_WORKERS
    run(max_workers=max_workers, schema_only=args.schema_only)


if __name__ == "__main__":
    main()
