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

-- =============================================================================
-- Historical archive (2016/17 through the last *completed* season), sourced
-- from vaastav/Fantasy-Premier-League + Understat (via that same repo).
--
-- Deliberately a SEPARATE schema from the live tables above, not bolted onto
-- them: the official live API is inherently season-less (it only ever
-- returns "now"), so the live tables key directly on the current season's
-- FPL ids. Historical data spans many seasons where those same numeric ids
-- get reused for different players/teams/fixtures year to year. The one
-- identifier confirmed stable across seasons AND across both data sources
-- is FPL's own `code` (player) / `team_code` (team) — verified this
-- directly against 5 real seasons of one real player before relying on it.
-- Every historical table below keys on (season, code), never the
-- season-local `id`.
--
-- Column availability genuinely varies by season (confirmed by fetching
-- real files, not assumed) — e.g. DEFCON's raw ingredients
-- (tackles/clearances_blocks_interceptions/recoveries/defensive_contribution)
-- only exist from 2025-26 onward; FPL's own expected_goals/expected_assists
-- only from 2022-23 onward. Rather than model every historical schema
-- variant, the small season-total tables also keep a `raw JSONB` column
-- with the full original row for anything not captured in typed columns —
-- cheap here since row counts are in the thousands, not hundreds of
-- thousands (unlike player_gameweek_stats below, which deliberately has NO
-- raw column — see that table's comment).
-- =============================================================================

CREATE TABLE IF NOT EXISTS historical_teams (
    id                      BIGSERIAL PRIMARY KEY,
    season                  TEXT NOT NULL,          -- vaastav's own format, e.g. '2016-17'
    team_code               INTEGER NOT NULL,        -- stable club identity (matches live teams.code)
    season_team_id          INTEGER,                 -- that season's numeric team id, informational only
    name                    TEXT,
    short_name              TEXT,
    -- teams.csv (source of name/short_name/strength) only exists from
    -- 2019-20 onward (verified directly: 404 for 2016-17..2018-19). For
    -- earlier seasons this row is still created (team_code/season_team_id
    -- recovered from players_raw.csv's own team/team_code columns) but
    -- name/short_name/strength stay NULL rather than being guessed.
    strength                SMALLINT,
    strength_overall_home   SMALLINT,
    strength_overall_away   SMALLINT,
    strength_attack_home    SMALLINT,
    strength_attack_away    SMALLINT,
    strength_defence_home   SMALLINT,
    strength_defence_away   SMALLINT,
    raw                     JSONB,
    source                  TEXT NOT NULL DEFAULT 'vaastav',
    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (season, team_code)
);

CREATE TABLE IF NOT EXISTS historical_players (
    id                                  BIGSERIAL PRIMARY KEY,
    season                              TEXT NOT NULL,
    player_code                         INTEGER NOT NULL,   -- stable identity (matches live players.code)
    season_element_id                   INTEGER,             -- that season's element id, informational only
    team_code                           INTEGER,
    first_name                          TEXT,
    second_name                         TEXT,
    web_name                            TEXT,
    position                            TEXT,                -- normalized short position (GKP/DEF/MID/FWD)
    start_cost                          INTEGER,             -- tenths of £m
    end_cost                            INTEGER,
    total_points                        INTEGER,
    minutes                             INTEGER,
    starts                              INTEGER,             -- NULL pre-introduction of this stat
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
    -- FPL's own (Opta-sourced) xG/xA — confirmed present in players_raw.csv
    -- only from 2024-25 onward; NULL for earlier seasons in this table.
    -- (Understat's independently-modeled xG/xA lives in the separate
    -- historical_understat_* tables below, joined by player_code.)
    expected_goals                      NUMERIC(6,2),
    expected_assists                    NUMERIC(6,2),
    expected_goal_involvements          NUMERIC(6,2),
    expected_goals_conceded             NUMERIC(6,2),
    -- DEFCON raw ingredients — confirmed present in players_raw.csv only
    -- from 2025-26 onward. defcon_recorded=true means these numbers
    -- actually earned real DEFCON bonus points that season (already
    -- reflected in total_points/bonus above) — false means either the
    -- columns are NULL (no data), or (rare, 2016-17 only) raw counts exist
    -- but predate DEFCON as a scoring rule entirely, so must never be
    -- presented as recorded scoring. Computing "what DEFCON points this
    -- would have been" for non-recorded seasons is the projections
    -- engine's job (Phase 3), not this table's.
    clearances_blocks_interceptions     INTEGER,
    recoveries                          INTEGER,
    tackles                             INTEGER,
    defensive_contribution              INTEGER,
    defcon_recorded                     BOOLEAN NOT NULL DEFAULT false,
    raw                                 JSONB NOT NULL,
    source                              TEXT NOT NULL DEFAULT 'vaastav',
    ingested_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (season, player_code)
);

CREATE INDEX IF NOT EXISTS idx_historical_players_code ON historical_players(player_code);
CREATE INDEX IF NOT EXISTS idx_historical_players_team ON historical_players(season, team_code);

-- One row per player per fixture they were involved in that season, from
-- vaastav's merged_gw.csv. Deliberately NO raw JSONB column here (unlike
-- the tables above) — this is the large table: one real season (2024-25)
-- measured at 27,605 rows from a 4.9MB CSV; ~10 seasons puts this table in
-- the hundreds of thousands of rows, where a JSONB blob per row would be
-- the single biggest driver of Neon's 0.5GB free-tier storage cap. Typed
-- columns only.
CREATE TABLE IF NOT EXISTS historical_player_gameweek_stats (
    id                                  BIGSERIAL PRIMARY KEY,
    season                              TEXT NOT NULL,
    player_code                         INTEGER NOT NULL,
    round                                SMALLINT NOT NULL,
    fixture_season_id                   INTEGER NOT NULL,   -- that season's `fixture` id from merged_gw.csv
    opponent_team_code                  INTEGER,
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
    expected_goals                      NUMERIC(6,2),
    expected_assists                    NUMERIC(6,2),
    expected_goal_involvements          NUMERIC(6,2),
    expected_goals_conceded             NUMERIC(6,2),
    clearances_blocks_interceptions     INTEGER,
    recoveries                          INTEGER,
    tackles                             INTEGER,
    defensive_contribution              INTEGER,
    defcon_recorded                     BOOLEAN NOT NULL DEFAULT false,
    value                               INTEGER,   -- price at kickoff, tenths of £m
    selected                            INTEGER,
    transfers_balance                   INTEGER,
    transfers_in                        INTEGER,
    transfers_out                       INTEGER,
    team_h_score                        SMALLINT,
    team_a_score                        SMALLINT,
    kickoff_time                        TIMESTAMPTZ,
    source                              TEXT NOT NULL DEFAULT 'vaastav',
    ingested_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Confirmed against a real 2024-25 merged_gw.csv (27,605 rows): (element,
    -- fixture) is unique with zero duplicates; double gameweeks are real
    -- (374 confirmed cases) and produce two distinct fixture ids for the
    -- same round, so `fixture` — not `round` — is the correct disambiguator.
    UNIQUE (season, player_code, fixture_season_id)
);

CREATE INDEX IF NOT EXISTS idx_hist_pgs_player ON historical_player_gameweek_stats(player_code);
CREATE INDEX IF NOT EXISTS idx_hist_pgs_season_round ON historical_player_gameweek_stats(season, round);

-- Understat team names (e.g. "Manchester United") don't reliably match
-- FPL's short_name/name strings — this small hand-curated seed table maps
-- them to the stable team_code, same "light manual curation" pattern the
-- project spec already anticipates for penalty-taker order. Populated by a
-- migration/seed step, not the ETL itself.
CREATE TABLE IF NOT EXISTS understat_team_name_map (
    understat_team_name   TEXT PRIMARY KEY,
    team_code             INTEGER NOT NULL
);

-- Team-match-level Understat data. Verified present (HTTP 200) for exactly
-- 2019-20 through 2024-25; absent 2016-17..2018-19 and 2025-26 (Understat
-- scraping lapsed for that season per the repo's own recent history).
CREATE TABLE IF NOT EXISTS historical_understat_team_stats (
    id              BIGSERIAL PRIMARY KEY,
    season          TEXT NOT NULL,
    team_code       INTEGER,   -- resolved via understat_team_name_map; NULL if unmapped rather than dropped
    match_date      TIMESTAMPTZ,
    was_home        BOOLEAN,
    xg              NUMERIC(6,2),
    xga             NUMERIC(6,2),
    npxg            NUMERIC(6,2),
    npxga           NUMERIC(6,2),
    deep            INTEGER,
    deep_allowed    INTEGER,
    scored          INTEGER,
    missed          INTEGER,
    xpts            NUMERIC(5,2),
    result          TEXT,   -- 'w' | 'd' | 'l'
    raw             JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'understat_via_vaastav',
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (season, team_code, match_date)
);

CREATE INDEX IF NOT EXISTS idx_hist_understat_team ON historical_understat_team_stats(team_code);

-- Season-total Understat player data. player_code is only resolvable for
-- the 2 seasons vaastav also ships an id_dict.csv for (verified directly:
-- 2021-22 and 2022-23 only, NOT "2021-22 onward" as originally assumed) —
-- for every other season these rows are stored unlinked (player_code NULL)
-- rather than dropped or fuzzy-matched by name, since a wrong name-based
-- join would be worse than an honest gap.
CREATE TABLE IF NOT EXISTS historical_understat_player_stats (
    id              BIGSERIAL PRIMARY KEY,
    season          TEXT NOT NULL,
    understat_id    INTEGER NOT NULL,
    player_code     INTEGER,   -- NULL outside 2021-22/2022-23 — see comment above
    player_name     TEXT NOT NULL,   -- Understat's own name string, kept even when unlinked
    team_title      TEXT,
    games           INTEGER,
    minutes         INTEGER,
    goals           INTEGER,
    xg              NUMERIC(6,2),
    assists         INTEGER,
    xa              NUMERIC(6,2),
    shots           INTEGER,
    key_passes      INTEGER,
    npg             INTEGER,
    npxg            NUMERIC(6,2),
    xg_chain        NUMERIC(6,2),
    xg_buildup      NUMERIC(6,2),
    raw             JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'understat_via_vaastav',
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (season, understat_id)
);

CREATE INDEX IF NOT EXISTS idx_hist_understat_player_code ON historical_understat_player_stats(player_code);
