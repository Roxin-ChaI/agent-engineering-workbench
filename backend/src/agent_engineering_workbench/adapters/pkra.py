import time
from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from agent_engineering_workbench.contracts import RunMetrics, RunResult, RunStatus


class PKRAProtocolError(RuntimeError):
    """Raised when a PKRA runner result violates the integration contract."""


class PKRAFinalResponseLike(Protocol):
    @property
    def content(self) -> str | None: ...


class PKRAResultLike(Protocol):
    @property
    def final_response(self) -> PKRAFinalResponseLike: ...

    @property
    def messages(self) -> Sequence[object]: ...

    @property
    def iterations(self) -> int: ...

    @property
    def tool_calls_executed(self) -> int: ...

    @property
    def termination_reason(self) -> StrEnum: ...


class PKRARunner(Protocol):
    def __call__(self, query: str) -> PKRAResultLike: ...


_TERMINATION_STATUS = {
    # PKRA v0.3.0 exposes no normal stopped reason; runtime limits raise.
    "final_response": RunStatus.COMPLETED,
}


class PKRAAdapter:
    def __init__(self, runner: PKRARunner) -> None:
        self._runner = runner

    def run(self, user_input: str) -> RunResult:
        query = user_input.strip()
        if not query:
            raise ValueError("user_input must not be empty")

        started_at = time.perf_counter()
        result = self._runner(query)
        finished_at = time.perf_counter()

        status = self._map_status(result.termination_reason)
        output = result.final_response.content
        if status is RunStatus.COMPLETED and (
            output is None or not output.strip()
        ):
            raise PKRAProtocolError(
                "PKRA completed result must include a non-empty final response"
            )

        duration_ms = (finished_at - started_at) * 1000
        if duration_ms < 0:
            raise PKRAProtocolError("PKRA execution clock moved backwards")

        # PKRA messages are intentionally not mapped because Workbench has no
        # lossless message-history contract.
        return RunResult(
            status=status,
            output=output,
            trace=(),
            metrics=RunMetrics(
                iterations=result.iterations,
                tool_calls=result.tool_calls_executed,
                duration_ms=duration_ms,
            ),
            sources=(),
            error=None,
        )

    @staticmethod
    def _map_status(termination_reason: StrEnum) -> RunStatus:
        try:
            return _TERMINATION_STATUS[termination_reason.value]
        except KeyError as exc:
            raise PKRAProtocolError(
                f"Unsupported PKRA termination reason: {termination_reason.value}"
            ) from exc
