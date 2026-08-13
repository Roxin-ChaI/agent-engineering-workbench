from fastapi.testclient import TestClient

from agent_engineering_workbench.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert response.headers["content-type"] == "application/json"
