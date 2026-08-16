from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum

import pytest

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.adapters import pkra
from agent_engineering_workbench.adapters.pkra import (
    PKRAAdapter,
    PKRAFinalResponseLike,
    PKRAProtocolError,
    PKRAResultLike,
)
from agent_engineering_workbench.contracts import RunResult, RunStatus


class FakeTerminationReason(StrEnum):
    FINAL_RESPONSE = "final_response"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FakeFinalResponse:
    content: str | None


@dataclass(frozen=True)
class FakePKRAResult:
    final_response: PKRAFinalResponseLike
    messages: tuple[object, ...]
    iterations: int
    tool_calls_executed: int
    termination_reason: StrEnum


class FakeRunner:
    def __init__(self, result: PKRAResultLike) -> None:
        self.result = result
        self.queries: list[str] = []

    def __call__(self, query: str) -> PKRAResultLike:
        self.queries.append(query)
        return self.result


def make_result(
    *,
    content: str | None = "Final answer",
    messages: tuple[object, ...] = ("private transcript",),
    iterations: int = 3,
    tool_calls_executed: int = 2,
    termination_reason: StrEnum = FakeTerminationReason.FINAL_RESPONSE,
) -> FakePKRAResult:
    return FakePKRAResult(
        final_response=FakeFinalResponse(content=content),
        messages=messages,
        iterations=iterations,
        tool_calls_executed=tool_calls_executed,
        termination_reason=termination_reason,
    )


def run_adapter(adapter: WorkbenchAdapter, user_input: str) -> RunResult:
    return adapter.run(user_input)


def test_completed_result_and_metrics_are_mapped() -> None:
    runner = FakeRunner(make_result(iterations=4, tool_calls_executed=7))

    result = run_adapter(PKRAAdapter(runner), "research question")

    assert result.status is RunStatus.COMPLETED
    assert result.output == "Final answer"
    assert result.metrics.iterations == 4
    assert result.metrics.tool_calls == 7
    assert result.metrics.duration_ms is not None
    assert result.error is None


def test_duration_uses_runner_elapsed_time_in_milliseconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    times = iter((20.25, 21.5))

    class FakeTime:
        @staticmethod
        def perf_counter() -> float:
            events.append("time")
            return next(times)

    class TimedRunner:
        def __call__(self, query: str) -> PKRAResultLike:
            assert query == "research question"
            events.append("run")
            return make_result(iterations=5, tool_calls_executed=6)

    monkeypatch.setattr(pkra, "time", FakeTime())

    result = PKRAAdapter(TimedRunner()).run("research question")

    assert events == ["time", "run", "time"]
    assert result.metrics.duration_ms == pytest.approx(1250.0)
    assert result.metrics.iterations == 5
    assert result.metrics.tool_calls == 6


def test_trace_sources_and_messages_are_not_mapped() -> None:
    messages = ({"tool": "knowledge_search", "secret": "not exposed"},)
    runner = FakeRunner(make_result(messages=messages))

    result = PKRAAdapter(runner).run("research question")

    assert result.trace == ()
    assert result.sources == ()
    assert "knowledge_search" not in repr(result)
    assert "not exposed" not in repr(result)


def test_query_is_trimmed_and_runner_is_called_once() -> None:
    runner = FakeRunner(make_result())

    PKRAAdapter(runner).run("  research question \n")

    assert runner.queries == ["research question"]


@pytest.mark.parametrize("user_input", ["", "   ", "\t\n"])
def test_empty_query_is_rejected_without_calling_runner(user_input: str) -> None:
    runner = FakeRunner(make_result())

    with pytest.raises(ValueError, match="user_input must not be empty"):
        PKRAAdapter(runner).run(user_input)

    assert runner.queries == []


@pytest.mark.parametrize("content", [None, "", "   "])
def test_completed_result_requires_non_empty_final_response(
    content: str | None,
) -> None:
    runner = FakeRunner(make_result(content=content))

    with pytest.raises(
        PKRAProtocolError,
        match="completed result must include a non-empty final response",
    ):
        PKRAAdapter(runner).run("research question")


def test_unknown_termination_reason_is_rejected() -> None:
    runner = FakeRunner(
        make_result(termination_reason=FakeTerminationReason.UNKNOWN)
    )

    with pytest.raises(
        PKRAProtocolError,
        match="Unsupported PKRA termination reason: unknown",
    ):
        PKRAAdapter(runner).run("research question")


def test_runner_exception_is_propagated_unchanged() -> None:
    expected_error = RuntimeError("PKRA failed")

    class FailingRunner:
        def __call__(self, query: str) -> PKRAResultLike:
            assert query == "research question"
            raise expected_error

    with pytest.raises(RuntimeError) as error:
        PKRAAdapter(FailingRunner()).run("research question")

    assert error.value is expected_error


def test_original_pkra_result_is_not_modified() -> None:
    original_result = make_result(messages=({"value": [1, 2, 3]},))
    snapshot = deepcopy(original_result)

    PKRAAdapter(FakeRunner(original_result)).run("research question")

    assert original_result == snapshot
