import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_engineering_workbench import dependencies, dev_server
from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.app import app
from agent_engineering_workbench.contracts import RunResult, RunStatus
from agent_engineering_workbench.dependencies import (
    get_knowledge_research_adapter,
    get_web_research_adapter,
)
from agent_engineering_workbench.dev_server import (
    FakeKnowledgeResearchAdapter,
    FakeWebResearchAdapter,
    get_fake_knowledge_research_adapter,
    get_fake_web_research_adapter,
)


@pytest.fixture(autouse=True)
def configure_fake_dependency() -> Iterator[None]:
    app.dependency_overrides[get_web_research_adapter] = (
        get_fake_web_research_adapter
    )
    app.dependency_overrides[get_knowledge_research_adapter] = (
        get_fake_knowledge_research_adapter
    )
    yield
    app.dependency_overrides.clear()


def run_adapter(adapter: WorkbenchAdapter, query: str) -> RunResult:
    return adapter.run(query)


def parse_sse_event_types(body: str) -> list[str]:
    return [
        block.splitlines()[0].removeprefix("event: ")
        for block in body.strip().split("\n\n")
    ]


def test_fake_adapter_satisfies_contract_and_returns_gui_fixture() -> None:
    result = run_adapter(FakeWebResearchAdapter(), "  local research question  ")

    assert result.status is RunStatus.COMPLETED
    assert result.output is not None
    assert "local research question" in result.output
    assert [event.name for event in result.trace] == [
        "question_received",
        "web_search",
        "final_answer",
    ]
    assert result.metrics.model_dump() == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 125.0,
    }
    assert [source.model_dump() for source in result.sources] == [
        {
            "title": "Fake Research Source One",
            "url": "https://example.com/fake-source-one",
        },
        {
            "title": "Fake Research Source Two",
            "url": "https://example.com/fake-source-two",
        },
    ]
    assert result.error is None


def test_dev_app_overrides_production_dependencies() -> None:
    assert app.dependency_overrides[get_web_research_adapter] is (
        get_fake_web_research_adapter
    )
    assert app.dependency_overrides[get_knowledge_research_adapter] is (
        get_fake_knowledge_research_adapter
    )


def test_rest_endpoint_returns_fake_result() -> None:
    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "  REST integration check  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "REST integration check" in payload["output"]
    assert [trace["name"] for trace in payload["trace"]] == [
        "question_received",
        "web_search",
        "final_answer",
    ]
    assert payload["metrics"] == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 125.0,
    }
    assert len(payload["sources"]) == 2


def test_sse_endpoint_replays_fake_result() -> None:
    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "SSE integration check"},
    )

    assert response.status_code == 200
    assert parse_sse_event_types(response.text) == [
        "started",
        "trace",
        "trace",
        "trace",
        "completed",
    ]
    blocks = response.text.strip().split("\n\n")
    terminal_payload = json.loads(
        blocks[-1].splitlines()[1].removeprefix("data: ")
    )
    assert terminal_payload["data"]["status"] == "completed"
    assert "SSE integration check" in terminal_payload["data"]["output"]


def test_fake_knowledge_adapter_returns_pkra_shaped_gui_fixture() -> None:
    result = run_adapter(
        FakeKnowledgeResearchAdapter(),
        "  indexed knowledge question  ",
    )

    assert result.status is RunStatus.COMPLETED
    assert result.output is not None
    assert "indexed knowledge question" in result.output
    assert result.metrics.model_dump() == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 140.0,
    }
    assert result.trace == ()
    assert result.sources == ()
    assert result.error is None


def test_knowledge_rest_endpoint_returns_fake_result_without_real_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "_load_pkra_public_api",
        lambda: pytest.fail("production PKRA runner must not be created"),
    )

    response = TestClient(app).post(
        "/api/research/knowledge",
        json={"query": "  Knowledge REST integration check  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "Knowledge REST integration check" in payload["output"]
    assert payload["metrics"] == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 140.0,
    }
    assert payload["trace"] == []
    assert payload["sources"] == []


def test_knowledge_sse_endpoint_returns_started_then_completed() -> None:
    response = TestClient(app).post(
        "/api/research/knowledge/stream",
        json={"query": "Knowledge SSE integration check"},
    )

    assert response.status_code == 200
    assert parse_sse_event_types(response.text) == ["started", "completed"]
    blocks = response.text.strip().split("\n\n")
    terminal_payload = json.loads(
        blocks[-1].splitlines()[1].removeprefix("data: ")
    )
    assert terminal_payload["data"]["status"] == "completed"
    assert terminal_payload["data"]["trace"] == []
    assert terminal_payload["data"]["sources"] == []
    assert "Knowledge SSE integration check" in terminal_payload["data"]["output"]


def test_main_uses_local_uvicorn_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_uvicorn_run(
        application: object,
        *,
        host: str,
        port: int,
        reload: bool,
    ) -> None:
        captured.update(
            application=application,
            host=host,
            port=port,
            reload=reload,
        )

    monkeypatch.setattr(dev_server.uvicorn, "run", fake_uvicorn_run)

    dev_server.main()

    assert captured == {
        "application": app,
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
    }
