"""FastAPI app entrypoint — deployed as its own Vercel project (see the
Phase 2 plan for why this is a separate project from the frontend rather
than Vercel Services: Services is currently in Public Beta).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import players, teams

app = FastAPI(title="FPL Analytics API")

# Comma-separated list of allowed frontend origins, e.g.
# "https://fpl-tracker.vercel.app,http://localhost:3000". Localhost is
# always allowed for local dev regardless of the env var.
_configured_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
_allowed_origins = list({*_configured_origins, "http://localhost:3000"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(players.router, prefix="/api")
app.include_router(teams.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
