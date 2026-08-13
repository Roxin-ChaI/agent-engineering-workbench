from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _ImmutableContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TraceEvent(_ImmutableContract):
    sequence: int = Field(ge=0)
    event_type: str
    name: str
    detail: str | None = None

    @field_validator("event_type", "name")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("must not be empty")
        return normalized_value


class RunMetrics(_ImmutableContract):
    iterations: int | None = Field(default=None, ge=0)
    tool_calls: int | None = Field(default=None, ge=0)
    duration_ms: float | None = Field(default=None, ge=0)


class SourceReference(_ImmutableContract):
    title: str
    url: str | None = None

    @field_validator("title")
    @classmethod
    def validate_non_empty_title(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("must not be empty")
        return normalized_value


class RunResult(_ImmutableContract):
    status: RunStatus
    output: str | None
    trace: tuple[TraceEvent, ...] = ()
    metrics: RunMetrics
    sources: tuple[SourceReference, ...] = ()
    error: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> Self:
        if self.status is RunStatus.COMPLETED:
            if self.output is None or not self.output.strip():
                raise ValueError("completed results require non-empty output")
            if self.error is not None:
                raise ValueError("completed results must not include an error")

        if self.status is RunStatus.FAILED and (
            self.error is None or not self.error.strip()
        ):
            raise ValueError("failed results require a non-empty error")

        return self
