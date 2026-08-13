import json
from typing import Protocol

from web_research_agent.models import (  # type: ignore[import-untyped]
    AgentResult,
    TraceStep,
)

from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    SourceReference,
    TraceEvent,
)


class _WRAAgent(Protocol):
    def run(self, question: str) -> AgentResult: ...


class WRAAdapter:
    def __init__(self, agent: _WRAAgent) -> None:
        self._agent = agent

    def run(self, user_input: str) -> RunResult:
        if not user_input.strip():
            raise ValueError("user_input must not be empty")

        result = self._agent.run(user_input)
        status = self._map_status(result)

        return RunResult(
            status=status,
            output=result.answer,
            trace=tuple(
                self._to_trace_event(sequence, step)
                for sequence, step in enumerate(result.trace)
            ),
            metrics=RunMetrics(
                iterations=result.iterations,
                tool_calls=len(result.trace),
                duration_ms=None,
            ),
            sources=self._extract_sources(result.trace),
        )

    @staticmethod
    def _map_status(result: AgentResult) -> RunStatus:
        if result.stop_reason == "completed":
            return RunStatus.COMPLETED
        if result.stop_reason == "max_iterations":
            return RunStatus.STOPPED
        raise ValueError(f"Unsupported WRA stop reason: {result.stop_reason}")

    @staticmethod
    def _to_trace_event(sequence: int, step: TraceStep) -> TraceEvent:
        return TraceEvent(
            sequence=sequence,
            event_type="tool_call",
            name=step.action.name,
            detail=None,
        )

    @classmethod
    def _extract_sources(
        cls,
        trace: tuple[TraceStep, ...],
    ) -> tuple[SourceReference, ...]:
        sources: list[SourceReference] = []
        seen: set[tuple[str, str | None]] = set()

        for step in trace:
            for source in cls._parse_observation_sources(step.observation):
                key = (source.title, source.url)
                if key not in seen:
                    seen.add(key)
                    sources.append(source)

        return tuple(sources)

    @staticmethod
    def _parse_observation_sources(observation: str) -> tuple[SourceReference, ...]:
        try:
            payload = json.loads(observation)
        except (json.JSONDecodeError, TypeError):
            return ()

        if not isinstance(payload, list):
            return ()

        sources: list[SourceReference] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            raw_url = item.get("url")
            url = raw_url if isinstance(raw_url, str) else None
            sources.append(SourceReference(title=title, url=url))

        return tuple(sources)
