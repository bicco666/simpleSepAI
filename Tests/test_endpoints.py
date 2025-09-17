from fastapi.testclient import TestClient
from Backend.app import app

client = TestClient(app)

def test_systemtest():
    r = client.get('/api/systemtest')
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert "Pass" in data['report']

def test_idea():
    r = client.get('/api/idea')
    assert r.status_code == 200
    assert "Kaufe 0,1 SOL" in r.json()['idea']

def test_analysis():
    r = client.get('/api/analysis')
    assert r.status_code == 200
    assert "Kaufe 0,1 SOL" in r.json()['analysis']

def test_execute():
    r = client.post('/api/execute', json={"sol": 0.01})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'address' in data
    assert 'balance' in data
    assert isinstance(data['log'], list)