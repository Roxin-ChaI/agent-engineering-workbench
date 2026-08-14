import json
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi.testclient import TestClient

from agent_engineering_workbench.app import app
from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    TraceEvent,
)
from agent_engineering_workbench.dependencies import get_web_research_adapter
from agent_engineering_workbench.streaming import (
    StreamEvent,
    StreamEventType,
    encode_sse_event,
)

SSEEvent = tuple[str, dict[str, object]]


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


def parse_sse(body: str) -> list[SSEEvent]:
    events: list[SSEEvent] = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event_type = lines[0].removeprefix("event: ")
        payload = json.loads(lines[1].removeprefix("data: "))
        assert isinstance(payload, dict)
        events.append((event_type, cast(dict[str, object], payload)))
    return events


def make_completed_result() -> RunResult:
    return RunResult(
        status=RunStatus.COMPLETED,
        output="Research complete",
        trace=(
            TraceEvent(sequence=0, event_type="tool_call", name="first"),
            TraceEvent(sequence=1, event_type="tool_call", name="second"),
        ),
        metrics=RunMetrics(iterations=2, tool_calls=2),
    )


def test_encode_sse_event_is_deterministic_and_preserves_unicode() -> None:
    event = StreamEvent(
        sequence=0,
        event_type=StreamEventType.STARTED,
        data={"status": "研究开始"},
    )

    assert encode_sse_event(event) == (
        'event: started\ndata: {"data":{"status":"研究开始"},"sequence":0}\n\n'
    )


def test_completed_stream_replays_trace_and_has_one_terminal_event() -> None:
    adapter = FakeAdapter(make_completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "private research question"},
    )
    events = parse_sse(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [event_type for event_type, _ in events] == [
        "started",
        "trace",
        "trace",
        "completed",
    ]
    assert [payload["sequence"] for _, payload in events] == [0, 1, 2, 3]
    assert [
        cast(dict[str, object], payload["data"])["name"]
        for event_type, payload in events
        if event_type == "trace"
    ] == ["first", "second"]
    assert sum(event_type in {"completed", "stopped", "error"} for event_type, _ in events) == 1
    assert cast(dict[str, object], events[-1][1]["data"])["status"] == "completed"
    assert "private research question" not in json.dumps(events[0], ensure_ascii=False)
    assert adapter.inputs == ["private research question"]


def test_stopped_result_maps_to_stopped_terminal_event() -> None:
    adapter = FakeAdapter(
        RunResult(
            status=RunStatus.STOPPED,
            output=None,
            metrics=RunMetrics(iterations=5, tool_calls=2),
        )
    )
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "research question"},
    )
    events = parse_sse(response.text)

    assert [event_type for event_type, _ in events] == ["started", "stopped"]
    assert cast(dict[str, object], events[-1][1]["data"])["status"] == "stopped"
    assert adapter.inputs == ["research question"]


def test_failed_result_maps_to_error_terminal_event() -> None:
    adapter = FakeAdapter(
        RunResult(
            status=RunStatus.FAILED,
            output=None,
            metrics=RunMetrics(iterations=1, tool_calls=0),
            error="safe failure",
        )
    )
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "research question"},
    )
    events = parse_sse(response.text)

    assert [event_type for event_type, _ in events] == ["started", "error"]
    assert cast(dict[str, object], events[-1][1]["data"])["status"] == "failed"


def test_empty_query_returns_422_without_calling_adapter() -> None:
    adapter = FakeAdapter(make_completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "   "},
    )

    assert response.status_code == 422
    assert adapter.inputs == []


def test_adapter_exception_produces_safe_error_event() -> None:
    secret_error = "SDK failed with api-key-secret and full query"

    class FailingAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, user_input: str) -> RunResult:
            self.calls += 1
            raise RuntimeError(f"{secret_error}: {user_input}")

    adapter = FailingAdapter()
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "private user query"},
    )
    events = parse_sse(response.text)

    assert [event_type for event_type, _ in events] == ["started", "error"]
    assert events[-1][1]["data"] == {
        "message": "web research execution failed"
    }
    assert secret_error not in response.text
    assert "private user query" not in response.text
    assert "completed" not in [event_type for event_type, _ in events]
    assert adapter.calls == 1


def test_rest_endpoint_behavior_is_unchanged() -> None:
    adapter = FakeAdapter(make_completed_result())
    app.dependency_overrides[get_web_research_adapter] = lambda: adapter

    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "research question"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert adapter.inputs == ["research question"]


def test_health_endpoint_behavior_is_unchanged() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
