from enum import StrEnum
from math import isclose
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _ImmutableContextContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContextCompressionStrategy(StrEnum):
    NO_COMPRESSION = "no_compression"
    TRUNCATION = "truncation"
    WINDOWED = "windowed"


class ContextMessage(_ImmutableContextContract):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None


class ContextCompressionInput(_ImmutableContextContract):
    messages: tuple[ContextMessage, ...]
    target_token_budget: int = Field(gt=0)
    max_token_budget: int = Field(gt=0)
    strategy: ContextCompressionStrategy

    @model_validator(mode="after")
    def validate_budgets(self) -> Self:
        if self.target_token_budget > self.max_token_budget:
            raise ValueError(
                "target_token_budget must not exceed max_token_budget"
            )
        return self


class ContextCompressionResult(_ImmutableContextContract):
    original_messages: tuple[ContextMessage, ...]
    compressed_messages: tuple[ContextMessage, ...]
    original_token_estimate: int = Field(ge=0)
    compressed_token_estimate: int = Field(ge=0)
    tokens_saved_estimate: int = Field(ge=0)
    compression_ratio: float = Field(ge=0, le=1)
    strategy: ContextCompressionStrategy
    duration_ms: float = Field(ge=0)
    compression_applied: bool
    compressed_message_count: int = Field(ge=0)
    preserved_message_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_token_metrics(self) -> Self:
        if self.compressed_token_estimate > self.original_token_estimate:
            raise ValueError(
                "compressed_token_estimate must not exceed "
                "original_token_estimate"
            )
        expected_saved = (
            self.original_token_estimate - self.compressed_token_estimate
        )
        if self.tokens_saved_estimate != expected_saved:
            raise ValueError("tokens_saved_estimate is inconsistent")
        expected_ratio = (
            self.compressed_token_estimate / self.original_token_estimate
            if self.original_token_estimate
            else 1.0
        )
        if not isclose(self.compression_ratio, expected_ratio):
            raise ValueError("compression_ratio is inconsistent")
        return self
