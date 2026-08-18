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

## Engineering standards — optimize for correctness, not speed
- **Never assume a schema — inspect it.** The official FPL API has no real documentation. Before writing code against any endpoint, actually fetch a live sample response and read the real field names/shapes. Same for third-party repos (FPL-Core-Insights, vaastav's archive, OpenFPL) — check the actual files/columns, don't infer from the repo name or README summary alone.
- **Never assume a library's API — verify it.** Check the installed package's actual docs or source before using a method signature from memory, especially for anything version-sensitive (PuLP/OR-Tools, FastAPI, Next.js).
- **A phase isn't done until it has passing tests, not until it runs once.** Unit tests for pure logic (scoring math, DEFCON thresholds, optimizer constraints). For the projections engine, backtest against a past season/gameweek with a known outcome and report actual error (MAE), not "looks reasonable." For the optimizer, assert constraint satisfaction programmatically (budget, squad composition, max-3-per-club) rather than eyeballing output. For the simulator, assert simulated probabilities sum correctly and sanity-check against an obvious case.
- **Set up CI early.** A GitHub Actions workflow that runs the test suite on every push (free on this public repo) — regressions get caught automatically, not by manual re-review.
- **Use plan mode for non-trivial phases** (the synergy model, optimizer, simulator) — review the proposed approach before code gets written, not after.
- **No silent shortcuts.** Don't stub or mock critical logic and present it as done. If something is genuinely uncertain, say so and ask — don't guess quietly and move on.

## Build order
1. Data foundation — ETL + Postgres schema ← **current phase**
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
