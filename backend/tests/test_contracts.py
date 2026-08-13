import pytest
from pydantic import ValidationError

from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    SourceReference,
    TraceEvent,
)


def test_valid_completed_result() -> None:
    result = RunResult(
        status=RunStatus.COMPLETED,
        output="Research complete",
        metrics=RunMetrics(iterations=2, tool_calls=1, duration_ms=42.5),
    )

    assert result.status is RunStatus.COMPLETED
    assert result.output == "Research complete"
    assert result.error is None


def test_completed_result_without_output_is_rejected() -> None:
    with pytest.raises(ValidationError, match="require non-empty output"):
        RunResult(
            status=RunStatus.COMPLETED,
            output="   ",
            metrics=RunMetrics(),
        )


def test_completed_result_with_error_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not include an error"):
        RunResult(
            status=RunStatus.COMPLETED,
            output="Research complete",
            metrics=RunMetrics(),
            error="Unexpected error",
        )


def test_failed_result_without_error_is_rejected() -> None:
    with pytest.raises(ValidationError, match="require a non-empty error"):
        RunResult(
            status=RunStatus.FAILED,
            output=None,
            metrics=RunMetrics(),
        )


def test_stopped_result_is_valid_without_output_or_error() -> None:
    result = RunResult(
        status=RunStatus.STOPPED,
        output=None,
        metrics=RunMetrics(),
    )

    assert result.status is RunStatus.STOPPED
    assert result.output is None
    assert result.error is None


def test_negative_trace_sequence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TraceEvent(sequence=-1, event_type="agent", name="started")


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("iterations", -1), ("tool_calls", -1), ("duration_ms", -0.1)],
)
def test_negative_metrics_are_rejected(field_name: str, value: float) -> None:
    with pytest.raises(ValidationError):
        RunMetrics.model_validate({field_name: value})


def test_empty_source_title_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceReference(title="   ")


def test_tuple_order_is_preserved() -> None:
    first_event = TraceEvent(sequence=0, event_type="agent", name="started")
    second_event = TraceEvent(sequence=1, event_type="tool", name="searched")
    first_source = SourceReference(title="First")
    second_source = SourceReference(title="Second")

    result = RunResult(
        status=RunStatus.COMPLETED,
        output="Research complete",
        trace=(first_event, second_event),
        metrics=RunMetrics(),
        sources=(first_source, second_source),
    )

    assert result.trace == (first_event, second_event)
    assert result.sources == (first_source, second_source)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        TraceEvent.model_validate(
            {
                "sequence": 0,
                "event_type": "agent",
                "name": "started",
                "unknown": True,
            }
        )
