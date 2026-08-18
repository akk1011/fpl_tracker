# FPL Analytics Platform — Project Spec (v1)

## 1. Vision

A hosted, public Fantasy Premier League analytics platform, open to any FPL manager — not just a personal team tracker, but a full player/team intelligence tool covering underlying performance metrics, points projections (including the new DEFCON rule), transfer decision support, player-synergy/injury-impact analysis, chip tracking, a mini-league simulator, and an eventual chatbot layer on top of it all. Built and run at $0/month for now.

Built primarily via an AI coding agent (Claude Code) doing the implementation, with this doc as the seed brief.

## 2. Data Sources

| Source | What it gives you | Notes |
|---|---|---|
| **Official FPL API** (`fantasy.premierleague.com/api`) | Players, teams, fixtures, gameweeks, live scores, manager teams/history/chips, mini-league standings | Free, no auth. **CORS-blocked** — must be called server-side, never directly from the frontend. No official docs; field names can shift between seasons (check every July). |
| **[olbauday/FPL-Core-Insights](https://github.com/olbauday/FPL-Core-Insights)** | Official FPL data fused with detailed match stats + dynamic Elo ratings, aligned to FPL IDs | Actively maintained for 2026/27. Likely your richest single source. |
| **[vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League)** | Historical archive back to 2016/17, merged with Understat xG/xA | Good for backtesting/training projection models. |
| **Understat** | Raw xG, xA, xGI, xGC | Usually consumed via the two repos above rather than scraped directly. |
| **[daniegr/OpenFPL](https://github.com/daniegr/OpenFPL)** | Open-source, MIT-licensed ensemble ML model (XGBoost + Random Forest) for expected points, published research showing it's competitive with commercial FPL projection services | Trained on data through 2023-24, i.e. **pre-DEFCON** — usable as an xP baseline but needs an added DEFCON feature set. |

### Key official FPL endpoints

```
GET /bootstrap-static/                          # all players, teams, gameweeks, prices — call this first
GET /fixtures/                                   # all fixtures (add ?event=GW for one gameweek)
GET /element-summary/{player_id}/                # full per-player match history + FDR
GET /event/{gw}/live/                            # live scores for a gameweek
GET /entry/{team_id}/                             # a manager's basic info
GET /entry/{team_id}/history/                     # season history + chips played
GET /entry/{team_id}/event/{gw}/picks/            # a manager's squad for a given gameweek
GET /leagues-classic/{league_id}/standings/       # mini-league table
```

## 3. Core Scoring Rules to Encode (2025/26 → 2026/27, confirmed unchanged)

- Standard scoring: goals, assists, clean sheets, cards, saves, bonus (BPS).
- **DEFCON (Defensive Contribution)**, new for 2025/26:
  - Defenders: **+2 points** for 10+ combined Clearances, Blocks, Interceptions, Tackles (CBIT) in a match.
  - Midfielders/Forwards: **+2 points** for 12+ CBIT + Ball Recoveries (CBIRT) in a match.
  - Capped at +2 per player per match regardless of volume above the threshold.
  - Goalkeepers are not eligible.

## 4. Underlying Metrics to Track

- **Player-level**: xG, xGC (expected goals conceded while on pitch)
- **Team-level**: xG, xGA (feeds a better fixture-difficulty rating than FPL's own static FDR)
- **Penalties**: penalty xG vs. open-play xG, penalty-taker order (needs light manual curation — not officially published)
- Refresh cadence: **daily** batch refresh for v1 (live in-match polling is a heavier, separate tier — not in scope yet)

## 5. USP / Competitive Positioning

A landscape check turned up real competition on most of the "obvious" features — xG dashboards, DEFCON trackers, chip planners, and AI chatbots tied to a live team all already exist elsewhere (Fantasy Football Fix, FFH, Draft Fantasy, ChatFPL, FPL-GPT, FPLai, FPL Pulse, among others). Build these well — they're necessary — but don't market them as the differentiator.

Two things are genuinely underserved:

1. **Player synergy / injury-impact modeling** — quantifying how a player's underlying output shifts when a specific teammate starts vs. doesn't. No FPL tool productizes this well.
2. **A simulator tied to your actual mini-league** — not generic rank projections, but Monte Carlo outcomes for your specific group's real teams. Commercial tools can't offer this because it depends on data only your group has.

The chatbot becomes a real differentiator *because* it can reason over #1 and #2 — nobody else's assistant has access to that analysis.

## 6. Feature Modules (build in this order)

1. **Data foundation** — ETL pulling official API + FPL-Core-Insights into Postgres. Nothing else works without this.
2. **Core dashboards** — player/team pages: underlying metrics (xG, xGC, xA, xGA, DEFCON actions, penalties, BPS breakdown) mapped to how they convert into FPL points.
3. **Projections engine** — xP model (OpenFPL baseline + DEFCON extension), plus separate goals/assists projections. Everything below reuses this.
4. **Transfer decision support** — short-term (next 1–3 GWs) and long-term (fixture-run) suggestions, built on the projections engine + price-change risk modeling.
5. **Budget & transfer optimizer** — constrained optimization (PuLP/OR-Tools): best possible 15 for £100m under squad rules, plus a multi-gameweek transfer optimizer that weighs point gain against hit cost.
6. **Synergy / injury-impact analysis** — *the hardest, most bespoke piece.* No off-the-shelf API for this — it's a custom co-occurrence module: compare a player's underlying output in matches a specific teammate started vs. didn't. Needs match-lineup-level data (FPL-Core-Insights has starting XIs).
7. **Chip tracker & optimizer** — Bench Boost / Triple Captain / Free Hit / Wildcard usage pulled straight from `entry/{id}/history/` (the `chips` field). Timing-suggestion logic layers on top once projections are reliable.
8. **Mini-league simulator** — Monte Carlo season simulation for a specific mini-league: snapshot all managers' squads, model point variance (not just averages) from historical residuals, run ~10,000 simulated playthroughs, report win/rank probabilities. Re-run weekly with real squads rather than trying to predict rivals' future transfers.
9. **Multi-user support** — any manager pastes their own public FPL team ID; the same engine (projections, optimizer, chatbot) runs against their squad. No login system needed.
10. **Hosting & sharing** — public-facing deployment (see open questions below).
11. **Chatbot layer** — see LLM strategy below; tool-calls into your own backend endpoints so it answers from real data/analysis, not general knowledge.

## 7. Suggested Architecture (optimized for $0)

- **Repo**: public on GitHub — unlocks unlimited free GitHub Actions minutes (vs. a capped allowance on private repos), which doubles as the "share it openly" goal.
- **Ingestion + heavy compute**: Python job on GitHub Actions cron (daily). This is also where the mini-league simulator's Monte Carlo runs happen — precomputed and cached, never run live per request, since a free serverless function can't finish a 10,000-run simulation inside its execution limit.
- **Storage**: Postgres on **Neon** (free tier) — holds raw API snapshots, processed tables, and precomputed simulation results.
- **Backend**: Python serverless functions on **Vercel** (not a separate always-on host) — proxies the FPL API (required, due to CORS) and serves REST endpoints reading from Postgres.
- **Frontend**: Next.js + Tailwind, same Vercel deployment.
- **Domain**: free `*.vercel.app` subdomain for now; a custom domain (~$10–15/year) is the one likely eventual cost.

## 8. Chatbot & LLM Strategy

- **Start on an open-weight model** (Qwen 3.6/3.7 or GLM-5.1 — both known for reliable tool-calling under permissive licenses) via a hosted inference provider (Groq, Together.ai, Fireworks.ai, or OpenRouter). Near-$0 cost to start; no GPU management needed.
- **Build behind a provider-agnostic wrapper** — either a single internal `ask_llm(messages, tools)` function, or the open-source **LiteLLM** library — so switching providers later is a config change, not a rewrite. This matters because Anthropic's API schema differs from the OpenAI-compatible format most open-model providers use.
- **Rate-limit chatbot usage per user/IP** — free inference tiers cap requests per minute/day; this is the real ceiling for a public tool, not cost. Fail gracefully ("high demand, try again shortly") rather than hard-erroring.
- **Migration/routing path** (later, not now): once there's real usage and appetite to spend, either fully migrate to Claude API (Sonnet 5: $2/$10 per million input/output tokens; Haiku 4.5: $1/$5) or route routine lookups to the free open model and harder analytical questions (e.g. explaining synergy/injury-impact reasoning) to Claude.

## 9. Estimated Costs (all-in)

**Target: $0/month for now.** Achievable with: public repo (unlimited free GitHub Actions minutes), Vercel free tier for frontend + serverless backend, Neon free tier for Postgres, and a free-tier open-weight model (Groq/OpenRouter) for the chatbot, rate-limited per user.

The two things that will eventually push past $0, in order of likelihood:
1. Neon free-tier storage, if you keep multiple seasons of match-level detail data — watch this, upgrade only when you actually hit the ceiling.
2. Claude API, if/when you decide the chatbot needs frontier-model quality for the harder reasoning questions — optional, not required for launch.

## 10. Open Questions to Settle Before/During Build

- **Team ID input**: FPL manager IDs are public (no login required to view a team) — is the flow just "paste your team ID," or do you want optional accounts for saved views?
- **Model complexity for v1**: start with OpenFPL's baseline approach, or go straight to a custom model? (Recommend: baseline first, iterate.)

## 11. Scaling Path (if usage grows)

- **Frontend, backend, database**: plan upgrades only (Vercel Pro, Neon paid tier) — no re-architecture. The daily batch + cache pattern (compute once nightly, serve reads all day) means compute cost barely moves with user count.
- **Chatbot**: the one real ceiling. Free-tier LLM rate limits don't grow with demand — hitting them means paying (Claude API or a paid inference tier), but since it's behind a provider-agnostic wrapper, that's a config change, not a rewrite.
- **Not built in v1, additive if wanted later**: user accounts/saved views (real but contained new work), live in-match polling (separate, heavier architecture).

## 12. Suggested First Prompt for Claude Code

> Build Phase 1 of an FPL analytics platform: a Python ETL that pulls data from the official FPL API (bootstrap-static, fixtures, element-summary) and stores it in a Postgres database (Neon free tier). Set up the schema for players, teams, gameweeks, and fixtures. Write it to run as a scheduled GitHub Actions job (this will be a public repo, so Actions minutes are free) rather than a long-running process. Reference: FPL_Tracker_Spec.md in this repo for full project context, including the $0-budget architecture constraints in section 7.

