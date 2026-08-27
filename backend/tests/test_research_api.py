from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent_engineering_workbench.app import app
from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    SourceReference,
    TraceEvent,
)
from agent_engineering_workbench.dependencies import (
    get_knowledge_research_adapter,
    get_web_research_adapter,
)


class FakeAdapter:
    def __init__(self, result: RunResult) -> None:
        self.result = result
        self.inputs: list[str] = []

    def run(self, user_input: str) -> RunResult:
        self.inputs.append(user_input)
        return self.result


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def completed_result() -> RunResult:
    return RunResult(
        status=RunStatus.COMPLETED,
        output="Research complete",
        trace=(
            TraceEvent(
                sequence=0,
                event_type="tool_call",
                name="web_search",
                detail=None,
            ),
        ),
        metrics=RunMetrics(iterations=2, tool_calls=1, duration_ms=None),
        sources=(
            SourceReference(title="Example", url="https://example.com"),
        ),
    )


def test_completed_research_returns_expected_json() -> None:
    adapter = FakeAdapter(completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "research question"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "output": "Research complete",
        "trace": [
            {
                "sequence": 0,
                "event_type": "tool_call",
                "name": "web_search",
                "detail": None,
            }
        ],
        "metrics": {"iterations": 2, "tool_calls": 1, "duration_ms": None},
        "sources": [{"title": "Example", "url": "https://example.com"}],
        "error": None,
    }
    assert adapter.inputs == ["research question"]


def test_stopped_research_returns_expected_json() -> None:
    adapter = FakeAdapter(
        RunResult(
            status=RunStatus.STOPPED,
            output=None,
            metrics=RunMetrics(iterations=5, tool_calls=2),
        )
    )
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "research question"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "stopped",
        "output": None,
        "trace": [],
        "metrics": {"iterations": 5, "tool_calls": 2, "duration_ms": None},
        "sources": [],
        "error": None,
    }


def test_query_is_normalized_and_adapter_is_called_once() -> None:
    adapter = FakeAdapter(completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "  research question  "},
    )

    assert response.status_code == 200
    assert adapter.inputs == ["research question"]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {},
        {"query": "research question", "unknown": True},
    ],
)
def test_invalid_request_returns_422(payload: dict[str, object]) -> None:
    adapter = FakeAdapter(completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post("/api/research/web", json=payload)

    assert response.status_code == 422
    assert adapter.inputs == []


def test_adapter_exception_is_not_converted_to_completed_result() -> None:
    expected_error = RuntimeError("research failed")

    class FailingAdapter:
        def run(self, user_input: str) -> RunResult:
            del user_input
            raise expected_error

    app.dependency_overrides[get_web_research_adapter] = FailingAdapter

    with pytest.raises(RuntimeError) as error:
        TestClient(app).post(
            "/api/research/web",
            json={"query": "research question"},
        )

    assert error.value is expected_error


def test_health_endpoint_remains_available() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.5.0"}


def test_completed_knowledge_research_returns_expected_json() -> None:
    adapter = FakeAdapter(
        RunResult(
            status=RunStatus.COMPLETED,
            output="Knowledge research complete",
            metrics=RunMetrics(
                iterations=3,
                tool_calls=2,
                duration_ms=412.5,
            ),
        )
    )
    app.dependency_overrides[get_knowledge_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/knowledge",
        json={"query": "  indexed knowledge question  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "output": "Knowledge research complete",
        "trace": [],
        "metrics": {
            "iterations": 3,
            "tool_calls": 2,
            "duration_ms": 412.5,
        },
        "sources": [],
        "error": None,
    }
    assert adapter.inputs == ["indexed knowledge question"]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {},
        {"query": "knowledge question", "unknown": True},
    ],
)
def test_invalid_knowledge_request_returns_422(
    payload: dict[str, object],
) -> None:
    adapter = FakeAdapter(completed_result())
    app.dependency_overrides[get_knowledge_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/knowledge",
        json=payload,
    )

    assert response.status_code == 422
    assert adapter.inputs == []


def test_malformed_knowledge_request_returns_standard_validation_error() -> None:
    adapter = FakeAdapter(completed_result())
    app.dependency_overrides[get_knowledge_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/knowledge",
        content=b'{"query":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"
    assert adapter.inputs == []


def test_knowledge_adapter_exception_uses_existing_rest_semantics() -> None:
    expected_error = RuntimeError("knowledge research failed")

    class FailingAdapter:
        def run(self, user_input: str) -> RunResult:
            del user_input
            raise expected_error

    app.dependency_overrides[get_knowledge_research_adapter] = FailingAdapter

    with pytest.raises(RuntimeError) as error:
        TestClient(app).post(
            "/api/research/knowledge",
            json={"query": "knowledge question"},
        )

    assert error.value is expected_error
