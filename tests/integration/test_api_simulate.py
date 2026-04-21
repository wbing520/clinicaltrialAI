from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_simulate_endpoint_returns_result():
    payload = {"condition_snomed": ["44054006"], "min_age": 60, "max_age": 80}
    resp = client.post("/simulate/", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert {"protocol", "cohort_size", "judge_score"}.issubset(data.keys())
