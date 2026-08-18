-- Seed data for understat_team_name_map (see db/schema.sql for why this
-- table exists — Understat's filename team strings don't match FPL's
-- name/short_name fields).
--
-- team_code values below are only included where fetched directly from a
-- real teams.csv this session (2024-25, 2025-26) — never guessed. The
-- Understat name half is confirmed against a real directory listing of
-- data/2024-25/understat/ for every row marked (verified); Leeds and
-- Sunderland are single-word club names so very likely correct under the
-- same convention, but were NOT in that 2024-25 listing (they weren't in
-- the PL that season) — marked (unverified naming).
--
-- INCOMPLETE BY DESIGN: doesn't yet cover clubs relegated before 2024-25
-- (Watford, Norwich, West Brom, Huddersfield, Swansea, Stoke, Hull,
-- Middlesbrough, Cardiff, QPR, Wigan, ...) — their team_code values haven't
-- been fetched from a real teams.csv yet. Complete this before the full
-- 9-season historical backfill (not needed for the 2025-26 pilot, which has
-- no Understat data at all — that season's understat/ folder is confirmed
-- absent).

INSERT INTO understat_team_name_map (understat_team_name, team_code) VALUES
    ('Arsenal', 3),                        -- verified
    ('Aston_Villa', 7),                    -- verified
    ('Bournemouth', 91),                   -- verified
    ('Brentford', 94),                     -- verified
    ('Brighton', 36),                      -- verified
    ('Burnley', 90),                       -- verified
    ('Chelsea', 8),                        -- verified
    ('Crystal_Palace', 31),                -- verified
    ('Everton', 11),                       -- verified
    ('Fulham', 54),                        -- verified
    ('Ipswich', 40),                       -- verified
    ('Leicester', 13),                     -- verified
    ('Liverpool', 14),                     -- verified
    ('Manchester_City', 43),               -- verified
    ('Manchester_United', 1),              -- verified
    ('Newcastle_United', 4),               -- verified
    ('Nottingham_Forest', 17),             -- verified
    ('Southampton', 20),                   -- verified
    ('Tottenham', 6),                      -- verified
    ('West_Ham', 21),                      -- verified
    ('Wolverhampton_Wanderers', 39),       -- verified
    ('Leeds', 2),                          -- unverified naming
    ('Sunderland', 56)                     -- unverified naming
ON CONFLICT (understat_team_name) DO UPDATE SET team_code = EXCLUDED.team_code;
