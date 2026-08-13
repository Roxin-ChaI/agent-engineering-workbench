from copy import deepcopy

import pytest
from pydantic import ValidationError
from web_research_agent.models import (  # type: ignore[import-untyped]
    AgentResult,
    ToolCall,
    TraceStep,
)

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.adapters.wra import WRAAdapter
from agent_engineering_workbench.contracts import (
    RunResult,
    RunStatus,
    SourceReference,
)


class FakeWRAAgent:
    def __init__(self, result: AgentResult) -> None:
        self.result = result
        self.questions: list[str] = []

    def run(self, question: str) -> AgentResult:
        self.questions.append(question)
        return self.result


def make_trace_step(
    call_id: str,
    query: str,
    observation: str,
) -> TraceStep:
    return TraceStep(
        action=ToolCall(
            id=call_id,
            name="web_search",
            arguments={"query": query},
        ),
        observation=observation,
    )


def run_adapter(adapter: WorkbenchAdapter, user_input: str) -> RunResult:
    return adapter.run(user_input)


def test_completed_result_is_mapped() -> None:
    agent = FakeWRAAgent(
        AgentResult(answer="Final answer", iterations=2, stop_reason="completed")
    )

    result = run_adapter(WRAAdapter(agent), "research question")

    assert result.status is RunStatus.COMPLETED
    assert result.output == "Final answer"
    assert result.metrics.iterations == 2
    assert result.metrics.duration_ms is None
    assert agent.questions == ["research question"]


def test_max_iterations_result_is_mapped_to_stopped() -> None:
    agent = FakeWRAAgent(
        AgentResult(answer=None, iterations=5, stop_reason="max_iterations")
    )

    result = WRAAdapter(agent).run("research question")

    assert result.status is RunStatus.STOPPED
    assert result.output is None


@pytest.mark.parametrize("user_input", ["", "   ", "\t\n"])
def test_empty_input_is_rejected(user_input: str) -> None:
    agent = FakeWRAAgent(AgentResult(answer="Unused"))

    with pytest.raises(ValueError, match="user_input must not be empty"):
        WRAAdapter(agent).run(user_input)

    assert agent.questions == []


def test_trace_order_and_tool_call_count_are_preserved() -> None:
    first_step = make_trace_step("call-1", "first", "not json")
    second_step = make_trace_step("call-2", "second", "also not json")
    agent = FakeWRAAgent(
        AgentResult(
            answer="Final answer",
            trace=(first_step, second_step),
            iterations=3,
        )
    )

    result = WRAAdapter(agent).run("research question")

    assert [event.sequence for event in result.trace] == [0, 1]
    assert [event.name for event in result.trace] == ["web_search", "web_search"]
    assert [event.event_type for event in result.trace] == ["tool_call", "tool_call"]
    assert result.metrics.tool_calls == 2


def test_sources_are_extracted_and_duplicates_are_removed() -> None:
    first_observation = """[
        {"title": "First", "url": "https://example.com/first", "snippet": "A"},
        {"title": "Second", "url": "https://example.com/second", "snippet": "B"},
        {"title": "", "url": "https://example.com/ignored"}
    ]"""
    second_observation = """[
        {"title": "First", "url": "https://example.com/first"},
        {"title": "Without URL"}
    ]"""
    agent = FakeWRAAgent(
        AgentResult(
            answer="Final answer",
            trace=(
                make_trace_step("call-1", "first", first_observation),
                make_trace_step("call-2", "second", second_observation),
            ),
        )
    )

    result = WRAAdapter(agent).run("research question")

    assert result.sources == (
        SourceReference(title="First", url="https://example.com/first"),
        SourceReference(title="Second", url="https://example.com/second"),
        SourceReference(title="Without URL", url=None),
    )


@pytest.mark.parametrize(
    "observation",
    ["not json", '{"title": "Not a list"}', '["Not an object"]'],
)
def test_invalid_observation_is_ignored(observation: str) -> None:
    agent = FakeWRAAgent(
        AgentResult(
            answer="Final answer",
            trace=(make_trace_step("call-1", "query", observation),),
        )
    )

    result = WRAAdapter(agent).run("research question")

    assert result.sources == ()


def test_unknown_stop_reason_is_rejected() -> None:
    result = AgentResult(answer="Final answer")
    object.__setattr__(result, "stop_reason", "unknown")
    agent = FakeWRAAgent(result)

    with pytest.raises(ValueError, match="Unsupported WRA stop reason"):
        WRAAdapter(agent).run("research question")


def test_wra_exception_is_propagated_unchanged() -> None:
    expected_error = RuntimeError("WRA failed")

    class FailingWRAAgent:
        def run(self, question: str) -> AgentResult:
            del question
            raise expected_error

    with pytest.raises(RuntimeError) as error:
        WRAAdapter(FailingWRAAgent()).run("research question")

    assert error.value is expected_error


def test_original_wra_result_is_not_modified() -> None:
    original_result = AgentResult(
        answer="Final answer",
        trace=(make_trace_step("call-1", "query", "[]"),),
        iterations=1,
    )
    snapshot = deepcopy(original_result)

    WRAAdapter(FakeWRAAgent(original_result)).run("research question")

    assert original_result == snapshot


def test_completed_result_without_answer_respects_run_result_contract() -> None:
    agent = FakeWRAAgent(
        AgentResult(answer=None, iterations=1, stop_reason="completed")
    )

    with pytest.raises(ValidationError):
        WRAAdapter(agent).run("research question")
