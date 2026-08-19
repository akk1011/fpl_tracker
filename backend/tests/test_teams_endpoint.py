ARSENAL_CODE = 3  # verified this session (Phase 1 Understat seed data)


def test_list_teams_returns_all_twenty(client):
    resp = client.get("/api/teams")
    assert resp.status_code == 200
    teams = resp.json()
    assert len(teams) == 20
    assert "squad_size" in teams[0]


def test_get_team_detail_includes_squad(client):
    resp = client.get(f"/api/teams/{ARSENAL_CODE}")
    assert resp.status_code == 200
    team = resp.json()
    assert team["code"] == ARSENAL_CODE
    assert team["name"] == "Arsenal"
    assert len(team["squad"]) > 0
    assert "web_name" in team["squad"][0]


def test_get_team_404_for_unknown_code(client):
    resp = client.get("/api/teams/999999")
    assert resp.status_code == 404
