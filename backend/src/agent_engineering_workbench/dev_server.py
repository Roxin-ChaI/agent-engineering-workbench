"""Local-only FastAPI entry point backed by deterministic fake integration data."""

import uvicorn

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.app import app
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)
from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    SourceReference,
    TraceEvent,
)
from agent_engineering_workbench.dependencies import (
    get_context_compression_adapter,
    get_knowledge_research_adapter,
    get_web_research_adapter,
)


class FakeWebResearchAdapter:
    """Return deterministic data for local GUI integration without external calls."""

    def run(self, user_input: str) -> RunResult:
        query = user_input.strip()
        if not query:
            raise ValueError("user_input must not be empty")

        return RunResult(
            status=RunStatus.COMPLETED,
            output=(
                "Local Fake Web Research result for "
                f'"{query}". No external services were called.'
            ),
            trace=(
                TraceEvent(
                    sequence=0,
                    event_type="request",
                    name="question_received",
                    detail=f'Normalized local query: "{query}"',
                ),
                TraceEvent(
                    sequence=1,
                    event_type="tool_call",
                    name="web_search",
                    detail="Returned deterministic local search fixtures.",
                ),
                TraceEvent(
                    sequence=2,
                    event_type="answer",
                    name="final_answer",
                    detail="Produced the local Fake Web Research result.",
                ),
            ),
            metrics=RunMetrics(
                iterations=2,
                tool_calls=1,
                duration_ms=125.0,
            ),
            sources=(
                SourceReference(
                    title="Fake Research Source One",
                    url="https://example.com/fake-source-one",
                ),
                SourceReference(
                    title="Fake Research Source Two",
                    url="https://example.com/fake-source-two",
                ),
            ),
            error=None,
        )


class FakeKnowledgeResearchAdapter:
    """Return PKRA-shaped local data without database or external calls."""

    def run(self, user_input: str) -> RunResult:
        query = user_input.strip()
        if not query:
            raise ValueError("user_input must not be empty")

        return RunResult(
            status=RunStatus.COMPLETED,
            output=(
                "Local Fake Knowledge Research result for "
                f'"{query}". No external services were called.'
            ),
            trace=(),
            metrics=RunMetrics(
                iterations=2,
                tool_calls=1,
                duration_ms=140.0,
            ),
            sources=(),
            error=None,
        )


class FakeContextCompressionAdapter:
    """Return deterministic Context Lab data without invoking CWC."""

    def compress(
        self,
        compression_input: ContextCompressionInput,
    ) -> ContextCompressionResult:
        original_messages = compression_input.messages
        if not original_messages:
            return ContextCompressionResult(
                original_messages=(),
                compressed_messages=(),
                original_token_estimate=0,
                compressed_token_estimate=0,
                tokens_saved_estimate=0,
                compression_ratio=1.0,
                strategy=compression_input.strategy,
                duration_ms=3.0,
                compression_applied=False,
                compressed_message_count=0,
                preserved_message_count=0,
            )

        if (
            compression_input.strategy
            is ContextCompressionStrategy.NO_COMPRESSION
        ):
            return ContextCompressionResult(
                original_messages=original_messages,
                compressed_messages=original_messages,
                original_token_estimate=120,
                compressed_token_estimate=120,
                tokens_saved_estimate=0,
                compression_ratio=1.0,
                strategy=compression_input.strategy,
                duration_ms=3.0,
                compression_applied=False,
                compressed_message_count=0,
                preserved_message_count=len(original_messages),
            )

        return ContextCompressionResult(
            original_messages=original_messages,
            compressed_messages=(
                ContextMessage(
                    role="assistant",
                    content=(
                        "Local fake context summary generated for GUI "
                        "integration."
                    ),
                ),
                original_messages[-1],
            ),
            original_token_estimate=120,
            compressed_token_estimate=48,
            tokens_saved_estimate=72,
            compression_ratio=0.4,
            strategy=compression_input.strategy,
            duration_ms=3.0,
            compression_applied=True,
            compressed_message_count=max(len(original_messages) - 1, 0),
            preserved_message_count=1,
        )


def get_fake_web_research_adapter() -> WorkbenchAdapter:
    return FakeWebResearchAdapter()


def get_fake_knowledge_research_adapter() -> WorkbenchAdapter:
    return FakeKnowledgeResearchAdapter()


def get_fake_context_compression_adapter() -> FakeContextCompressionAdapter:
    return FakeContextCompressionAdapter()


app.dependency_overrides[get_web_research_adapter] = (
    get_fake_web_research_adapter
)
app.dependency_overrides[get_knowledge_research_adapter] = (
    get_fake_knowledge_research_adapter
)
app.dependency_overrides[get_context_compression_adapter] = (
    get_fake_context_compression_adapter
)


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
