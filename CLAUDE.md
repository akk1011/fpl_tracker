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
