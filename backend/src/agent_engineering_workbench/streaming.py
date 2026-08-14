import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StreamEventType(StrEnum):
    STARTED = "started"
    TRACE = "trace"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class StreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=0)
    event_type: StreamEventType
    data: dict[str, object]


def encode_sse_event(event: StreamEvent) -> str:
    payload = {
        "data": event.data,
        "sequence": event.sequence,
    }
    encoded_data = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"event: {event.event_type.value}\ndata: {encoded_data}\n\n"
