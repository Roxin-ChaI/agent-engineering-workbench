from typing import Never

from fastapi.testclient import TestClient

from agent_engineering_workbench.app import app
from agent_engineering_workbench.dependencies import get_web_research_adapter

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.2.0"}
    assert response.headers["content-type"] == "application/json"


def test_health_allows_localhost_cors_origin() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )


def test_health_allows_loopback_cors_origin() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:3000"
    )


def test_health_does_not_allow_unknown_cors_origin() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_web_research_post_preflight_uses_cors_without_adapter() -> None:
    def fail_if_adapter_is_resolved() -> Never:
        raise AssertionError("WRA dependency must not be resolved for preflight")

    app.dependency_overrides[get_web_research_adapter] = fail_if_adapter_is_resolved
    try:
        response = client.options(
            "/api/research/web",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:3000"
    )
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers
