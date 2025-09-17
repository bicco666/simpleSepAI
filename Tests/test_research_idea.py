from fastapi.testclient import TestClient
from Backend.app import app

client = TestClient(app)

def test_research_idea_endpoint_exists():
    r = client.post("/api/research/idea", json={"risk": 2, "budget_sol": 0.05})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "payload" in data
    assert data["payload"]["budget_sol"] > 0

def test_idea_text_contains_required_phrase():
    r = client.get("/api/idea")
    assert r.status_code == 200
    j = r.json()
    assert "Kaufe 0,1 SOL" in j["idea"]