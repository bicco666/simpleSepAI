from fastapi.testclient import TestClient
from Backend.app import app
client = TestClient(app)

def test_health_has_timeout():
    r = client.get("/api/research/health"); assert r.status_code == 200
    j = r.json(); assert j["ok"] is True and isinstance(j["timeout_s"], int) and j["timeout_s"] > 0

def test_research_idea():
    r = client.post("/api/research/idea", json={"risk": 2, "budget_sol": 0.05})
    assert r.status_code == 200
    j = r.json(); assert j["ok"] is True
    p = j["payload"]; assert 1 <= p["risk"] <= 5 and p["budget_sol"] > 0 and isinstance(p["idea_id"], str)

def test_plain_idea_endpoint_contains_phrase():
    r = client.get("/api/idea"); assert r.status_code == 200
    j = r.json(); assert "Kaufe 0,1 SOL" in j["idea"]