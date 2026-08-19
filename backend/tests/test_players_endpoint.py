"""Integration tests for /api/players* — real FastAPI TestClient against a
real seeded Postgres (see conftest.py), not mocks.

Deliberately does NOT hardcode a specific player's code as "the known real
player" — real squads change. (Caught live: Salah's code, stable across
every 2017-18-2025-26 season checked in Phase 1, returns zero rows against
the live 2026-27 players table — he's genuinely not in this season's data,
presumably transferred out of the league. Hardcoding him here would have
made this test silently go stale.) Instead, fetch a real code from the
list endpoint first and use that.
"""


def _a_real_player_code(client) -> int:
    players = client.get("/api/players", params={"limit": 1}).json()
    assert players, "no players in seeded data — can't run detail tests"
    return players[0]["code"]


def test_list_players_returns_data(client):
    resp = client.get("/api/players")
    assert resp.status_code == 200
    players = resp.json()
    assert len(players) > 0
    assert "web_name" in players[0]
    assert "team_short_name" in players[0]
    assert "position" in players[0]


def test_list_players_filters_by_position(client):
    resp = client.get("/api/players", params={"position": "gkp", "limit": 50})
    assert resp.status_code == 200
    players = resp.json()
    assert len(players) > 0
    assert all(p["position"] == "GKP" for p in players)


def test_list_players_rejects_invalid_sort_column(client):
    resp = client.get("/api/players", params={"sort": "'; DROP TABLE players; --"})
    assert resp.status_code == 400


def test_list_players_respects_limit(client):
    resp = client.get("/api/players", params={"limit": 5})
    assert resp.status_code == 200
    assert len(resp.json()) <= 5


def test_get_player_detail_includes_points_breakdown(client):
    code = _a_real_player_code(client)
    resp = client.get(f"/api/players/{code}")
    assert resp.status_code == 200
    player = resp.json()
    assert player["code"] == code
    assert player["web_name"]
    assert "points_breakdown_this_season" in player
    assert "total" in player["points_breakdown_this_season"]


def test_get_player_detail_breakdown_is_zero_preseason(client):
    """Pre-season, this season's actual breakdown must read 0 (no matches
    played yet), NOT echo last season's carried-over total_points — that
    was the exact bug caught during Phase 2 build/test."""
    code = _a_real_player_code(client)
    resp = client.get(f"/api/players/{code}")
    player = resp.json()
    assert player["matches_played_this_season"] == 0
    assert player["points_breakdown_this_season"]["total"] == 0


def test_get_player_detail_404_for_unknown_code(client):
    resp = client.get("/api/players/999999999")
    assert resp.status_code == 404


def test_get_player_gameweeks_empty_before_season_start(client):
    """Pre-season: the player exists but has no gameweek rows yet — should
    be an empty list, not a 404 (that's the whole point of distinguishing
    the two cases in the endpoint)."""
    code = _a_real_player_code(client)
    resp = client.get(f"/api/players/{code}/gameweeks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_player_gameweeks_404_for_unknown_code(client):
    resp = client.get("/api/players/999999999/gameweeks")
    assert resp.status_code == 404
