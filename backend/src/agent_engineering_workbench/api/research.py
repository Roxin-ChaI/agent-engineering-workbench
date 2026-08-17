from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from starlette.responses import StreamingResponse

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.contracts import RunResult, RunStatus
from agent_engineering_workbench.dependencies import (
    get_knowledge_research_adapter,
    get_web_research_adapter,
)
from agent_engineering_workbench.streaming import (
    StreamEvent,
    StreamEventType,
    encode_sse_event,
)


class WebResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("query must not be empty")
        return normalized_value


router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("/web", response_model=RunResult)
async def run_web_research(
    request: WebResearchRequest,
    adapter: Annotated[WorkbenchAdapter, Depends(get_web_research_adapter)],
) -> RunResult:
    return adapter.run(request.query)


@router.post("/knowledge", response_model=RunResult)
async def run_knowledge_research(
    request: WebResearchRequest,
    adapter: Annotated[
        WorkbenchAdapter,
        Depends(get_knowledge_research_adapter),
    ],
) -> RunResult:
    return adapter.run(request.query)


@router.post("/web/stream")
async def stream_web_research(
    request: WebResearchRequest,
    adapter: Annotated[WorkbenchAdapter, Depends(get_web_research_adapter)],
) -> StreamingResponse:
    return StreamingResponse(
        _stream_web_research(adapter, request.query),
        media_type="text/event-stream",
    )


def _stream_web_research(
    adapter: WorkbenchAdapter,
    query: str,
) -> Iterator[str]:
    sequence = 0
    yield encode_sse_event(
        StreamEvent(
            sequence=sequence,
            event_type=StreamEventType.STARTED,
            data={"status": "started"},
        )
    )
    sequence += 1

    try:
        result = adapter.run(query)
    except Exception:  # noqa: BLE001
        yield encode_sse_event(
            StreamEvent(
                sequence=sequence,
                event_type=StreamEventType.ERROR,
                data={"message": "web research execution failed"},
            )
        )
        return

    for trace in result.trace:
        yield encode_sse_event(
            StreamEvent(
                sequence=sequence,
                event_type=StreamEventType.TRACE,
                data=trace.model_dump(mode="json"),
            )
        )
        sequence += 1

    terminal_event_types = {
        RunStatus.COMPLETED: StreamEventType.COMPLETED,
        RunStatus.STOPPED: StreamEventType.STOPPED,
        RunStatus.FAILED: StreamEventType.ERROR,
    }
    yield encode_sse_event(
        StreamEvent(
            sequence=sequence,
            event_type=terminal_event_types[result.status],
            data=result.model_dump(mode="json"),
        )
    )
