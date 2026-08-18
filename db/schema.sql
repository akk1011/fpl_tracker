-- FPL Analytics Platform — Phase 1 schema
-- Applied idempotently (IF NOT EXISTS everywhere) so the nightly ETL can just
-- run this every time rather than needing a separate migration step.
--
-- Design notes:
--   * Primary keys reuse the official FPL API's own ids (element id, team id,
--     event id, fixture id) instead of surrogate keys — they're stable and it
--     keeps joins/debugging simple against the raw API responses.
--   * "players"/"teams"/"gameweeks" are point-in-time snapshots, upserted in
--     place every run. "player_gameweek_stats" is the append-over-time fact
--     table (one row per player per fixture) that projections etc. will read.
--   * Money fields (now_cost, value) are stored as the API gives them: tenths
--     of a million, e.g. 80 = £8.0m. Convert at the display layer.

CREATE TABLE IF NOT EXISTS positions (
    id                  SMALLINT PRIMARY KEY,       -- FPL element_type
    singular_name       TEXT NOT NULL,
    singular_name_short TEXT NOT NULL,
    plural_name         TEXT NOT NULL,
    plural_name_short   TEXT NOT NULL,
    squad_min_play      SMALLINT,
    squad_max_play      SMALLINT
);

CREATE TABLE IF NOT EXISTS teams (
    id                      SMALLINT PRIMARY KEY,   -- FPL team id (1-20, changes meaning each season)
    code                    INTEGER NOT NULL,        -- stable club code across seasons
    name                    TEXT NOT NULL,
    short_name              TEXT NOT NULL,
    strength                SMALLINT,
    strength_overall_home   SMALLINT,
    strength_overall_away   SMALLINT,
    strength_attack_home    SMALLINT,
    strength_attack_away    SMALLINT,
    strength_defence_home   SMALLINT,
    strength_defence_away   SMALLINT,
    played                  SMALLINT,
    win                     SMALLINT,
    draw                    SMALLINT,
    loss                    SMALLINT,
    points                  SMALLINT,
    position                SMALLINT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gameweeks (
    id                      SMALLINT PRIMARY KEY,   -- FPL "event" id
    name                    TEXT NOT NULL,
    deadline_time           TIMESTAMPTZ NOT NULL,
    finished                BOOLEAN NOT NULL DEFAULT false,
    data_checked            BOOLEAN NOT NULL DEFAULT false,
    is_previous             BOOLEAN NOT NULL DEFAULT false,
    is_current              BOOLEAN NOT NULL DEFAULT false,
    is_next                 BOOLEAN NOT NULL DEFAULT false,
    average_entry_score     SMALLINT,
    highest_score           INTEGER,
    -- these reference player ids informally; no FK since load order would be
    -- circular (gameweeks are loaded before players) and they're just stats
    top_element             INTEGER,
    most_selected            INTEGER,
    most_transferred_in     INTEGER,
    most_captained          INTEGER,
    most_vice_captained     INTEGER,
    transfers_made           INTEGER,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS players (
    id                                  INTEGER PRIMARY KEY,   -- FPL element id (season-specific)
    code                                INTEGER NOT NULL,       -- stable across seasons
    team_id                             SMALLINT NOT NULL REFERENCES teams(id),
    position_id                         SMALLINT NOT NULL REFERENCES positions(id),
    first_name                          TEXT,
    second_name                         TEXT,
    web_name                            TEXT NOT NULL,
    status                              TEXT,           -- a=available, i=injured, d=doubtful, s=suspended, u=unavailable, n=not in squad
    news                                TEXT,
    chance_of_playing_this_round        SMALLINT,
    chance_of_playing_next_round        SMALLINT,
    now_cost                            INTEGER NOT NULL,   -- tenths of £m
    cost_change_start                   INTEGER,
    selected_by_percent                 NUMERIC(5,1),
    form                                NUMERIC(4,1),
    points_per_game                     NUMERIC(4,1),
    value_season                        NUMERIC(5,1),
    total_points                        INTEGER,
    event_points                        INTEGER,
    minutes                             INTEGER,
    starts                              INTEGER,
    goals_scored                        INTEGER,
    assists                             INTEGER,
    clean_sheets                        INTEGER,
    goals_conceded                      INTEGER,
    own_goals                           INTEGER,
    penalties_saved                     INTEGER,
    penalties_missed                    INTEGER,
    yellow_cards                        INTEGER,
    red_cards                           INTEGER,
    saves                               INTEGER,
    bonus                               INTEGER,
    bps                                 INTEGER,
    influence                           NUMERIC(6,1),
    creativity                          NUMERIC(6,1),
    threat                              NUMERIC(6,1),
    ict_index                           NUMERIC(6,1),
    -- DEFCON (2025/26+): clearances + blocks + interceptions + tackles (+ recoveries
    -- for MID/FWD) >= threshold earns +2 flat. Raw counts stored here; the
    -- points-conversion logic belongs to the projections engine, not the schema.
    clearances_blocks_interceptions     INTEGER,
    recoveries                          INTEGER,
    tackles                             INTEGER,
    defensive_contribution               INTEGER,
    expected_goals                      NUMERIC(5,2),
    expected_assists                    NUMERIC(5,2),
    expected_goal_involvements          NUMERIC(5,2),
    expected_goals_conceded             NUMERIC(5,2),
    transfers_in                        INTEGER,
    transfers_out                       INTEGER,
    transfers_in_event                  INTEGER,
    transfers_out_event                 INTEGER,
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_position ON players(position_id);

CREATE TABLE IF NOT EXISTS fixtures (
    id                       INTEGER PRIMARY KEY,   -- FPL fixture id
    code                     BIGINT,
    gameweek_id              SMALLINT REFERENCES gameweeks(id),  -- nullable: unscheduled fixtures have no event yet
    team_h_id                SMALLINT NOT NULL REFERENCES teams(id),
    team_a_id                SMALLINT NOT NULL REFERENCES teams(id),
    team_h_score             SMALLINT,
    team_a_score             SMALLINT,
    team_h_difficulty        SMALLINT,
    team_a_difficulty        SMALLINT,
    kickoff_time             TIMESTAMPTZ,
    finished                 BOOLEAN NOT NULL DEFAULT false,
    started                  BOOLEAN NOT NULL DEFAULT false,
    minutes                  SMALLINT,
    provisional_start_time   BOOLEAN NOT NULL DEFAULT false,
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fixtures_gameweek ON fixtures(gameweek_id);
CREATE INDEX IF NOT EXISTS idx_fixtures_team_h ON fixtures(team_h_id);
CREATE INDEX IF NOT EXISTS idx_fixtures_team_a ON fixtures(team_a_id);

-- One row per player per fixture they were involved in (from
-- element-summary/{id}'s "history" list). This is the core fact table
-- projections, DEFCON tracking, and synergy analysis will all read from.
CREATE TABLE IF NOT EXISTS player_gameweek_stats (
    id                                  BIGSERIAL PRIMARY KEY,
    player_id                           INTEGER NOT NULL REFERENCES players(id),
    fixture_id                          INTEGER NOT NULL REFERENCES fixtures(id),
    gameweek_id                         SMALLINT NOT NULL REFERENCES gameweeks(id),
    opponent_team_id                    SMALLINT REFERENCES teams(id),
    was_home                            BOOLEAN,
    total_points                        INTEGER,
    minutes                             INTEGER,
    starts                              INTEGER,
    goals_scored                        INTEGER,
    assists                             INTEGER,
    clean_sheets                        INTEGER,
    goals_conceded                      INTEGER,
    own_goals                           INTEGER,
    penalties_saved                     INTEGER,
    penalties_missed                    INTEGER,
    yellow_cards                        INTEGER,
    red_cards                           INTEGER,
    saves                               INTEGER,
    bonus                               INTEGER,
    bps                                 INTEGER,
    influence                           NUMERIC(6,1),
    creativity                          NUMERIC(6,1),
    threat                              NUMERIC(6,1),
    ict_index                           NUMERIC(6,1),
    clearances_blocks_interceptions     INTEGER,
    recoveries                          INTEGER,
    tackles                             INTEGER,
    defensive_contribution              INTEGER,
    expected_goals                      NUMERIC(5,2),
    expected_assists                    NUMERIC(5,2),
    expected_goal_involvements          NUMERIC(5,2),
    expected_goals_conceded             NUMERIC(5,2),
    value                               INTEGER,   -- player price at kickoff, tenths of £m
    selected                            INTEGER,
    transfers_balance                   INTEGER,
    transfers_in                        INTEGER,
    transfers_out                       INTEGER,
    team_h_score                        SMALLINT,
    team_a_score                        SMALLINT,
    kickoff_time                        TIMESTAMPTZ,
    updated_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (player_id, fixture_id)
);

CREATE INDEX IF NOT EXISTS idx_pgs_player ON player_gameweek_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_pgs_gameweek ON player_gameweek_stats(gameweek_id);
CREATE INDEX IF NOT EXISTS idx_pgs_fixture ON player_gameweek_stats(fixture_id);

-- Small raw JSON snapshots of the two whole-season endpoints, kept for
-- audit/debugging/reprocessing. Deliberately NOT storing raw per-player
-- element-summary payloads here (600+ players x daily runs would eat the
-- Neon free-tier storage cap fast) — player_gameweek_stats already holds
-- the processed version of that data.
CREATE TABLE IF NOT EXISTS raw_snapshots (
    id           BIGSERIAL PRIMARY KEY,
    source       TEXT NOT NULL,     -- 'bootstrap_static' | 'fixtures'
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload      JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_snapshots_source_fetched ON raw_snapshots(source, fetched_at DESC);

-- One row per ETL run, for observability (did last night's job succeed?).
CREATE TABLE IF NOT EXISTS etl_runs (
    id                          BIGSERIAL PRIMARY KEY,
    started_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at                 TIMESTAMPTZ,
    status                      TEXT NOT NULL DEFAULT 'running',  -- running | success | failed
    detail                      TEXT,
    teams_upserted              INTEGER,
    players_upserted            INTEGER,
    fixtures_upserted           INTEGER,
    gameweek_stats_upserted     INTEGER
);
