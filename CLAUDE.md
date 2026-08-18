# FPL Analytics Platform

Public, hosted FPL analytics tool, open to any FPL manager. Full context and phase-by-phase feature detail: @FPL_Tracker_Spec.md

## Stack
- Ingestion + heavy compute (daily batch): Python, scheduled via GitHub Actions cron
- Storage: Postgres on Neon (free tier)
- Backend: Python serverless functions on Vercel
- Frontend: Next.js + Tailwind, deployed on Vercel

## Hard constraints — do not violate these
- **$0/month budget target.** No paid services, tiers, or upgrades without explicit approval first.
- **Heavy compute never runs live per-request.** Monte Carlo simulations and full projection runs happen in the nightly GitHub Actions batch job only, and get cached in Postgres. A free serverless function cannot finish a 10,000-run simulation inside its execution limit — don't try.
- **The official FPL API is CORS-blocked.** Always call it server-side (from the backend), never from frontend code.
- **Repo stays public** — this is what makes GitHub Actions minutes free.
- **Every table that grows on a recurring cadence needs a retention policy designed in at creation time, not bolted on later.** Found the hard way: `raw_snapshots` shipped with no limit and would have consumed ~475MB/year — most of Neon's entire 0.5GB free-tier cap — from one table alone, from a single nightly insert with no pruning. A one-time historical backfill isn't this risk (it lands once and stops); anything that inserts on a schedule forever is. The next concrete case: **Phase 8's mini-league simulator caches Monte Carlo results** — design its retention (e.g. keep latest per league, or last N runs) as part of that table's schema, not as a follow-up fix.

## Engineering standards — optimize for correctness, not speed
- **Never assume a schema — inspect it.** The official FPL API has no real documentation. Before writing code against any endpoint, actually fetch a live sample response and read the real field names/shapes. Same for third-party repos (FPL-Core-Insights, vaastav's archive, OpenFPL) — check the actual files/columns, don't infer from the repo name or README summary alone.
- **Never assume a library's API — verify it.** Check the installed package's actual docs or source before using a method signature from memory, especially for anything version-sensitive (PuLP/OR-Tools, FastAPI, Next.js).
- **A phase isn't done until it has passing tests, not until it runs once.** Unit tests for pure logic (scoring math, DEFCON thresholds, optimizer constraints). For the projections engine, backtest against a past season/gameweek with a known outcome and report actual error (MAE), not "looks reasonable." For the optimizer, assert constraint satisfaction programmatically (budget, squad composition, max-3-per-club) rather than eyeballing output. For the simulator, assert simulated probabilities sum correctly and sanity-check against an obvious case.
- **Set up CI early.** A GitHub Actions workflow that runs the test suite on every push (free on this public repo) — regressions get caught automatically, not by manual re-review.
- **Use plan mode for non-trivial phases** (the synergy model, optimizer, simulator) — review the proposed approach before code gets written, not after.
- **No silent shortcuts.** Don't stub or mock critical logic and present it as done. If something is genuinely uncertain, say so and ask — don't guess quietly and move on.

## Build order
1. Data foundation — ETL + Postgres schema. **Historical depth: full archive, 2016/17 through the current season (~10 seasons)** via vaastav's repo, plus daily live ingestion of the current season via the official API. DEFCON only has real recorded data from 2025/26 onward — any DEFCON figures computed for earlier seasons are a derived backfill from raw defensive-action stats and must be labeled as such, never presented as recorded scoring. Includes Understat xG/xA — verified directly against live files (not the README's implied "merged" coverage): team-level is broad (2019-20–2024-25), but player-level linkage to FPL identity only works for 2021-22 and 2022-23 (the only seasons vaastav also ships an `id_dict.csv` for); see FPL_Tracker_Spec.md §2 for the full detail. ← **current phase**
2. Core dashboards
3. Projections engine (xP, DEFCON/goals/assists)
4. Transfer decision support
5. Budget & transfer optimizer
6. Synergy / injury-impact analysis
7. Chip tracker & optimizer
8. Mini-league simulator
9. Multi-user support (paste-your-team-ID, no login)
10. Hosting & sharing
11. Chatbot — start on an open-weight model (Qwen 3.6/3.7 or GLM-5.1) via Groq/OpenRouter free tier, behind a provider-agnostic wrapper so a future move to Claude API is a config change, not a rewrite.

Update this file after any major architectural decision — keep it short; put detail in the spec, not here.
