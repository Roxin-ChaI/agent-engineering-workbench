from enum import StrEnum
from math import isclose
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _ImmutablePromptContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PromptExperimentVariant(StrEnum):
    BASELINE = "baseline"
    TONE_TRUMP = "tone_trump"
    TONE_CASUAL = "tone_casual"
    WIKI_RANDOM = "wiki_random"
    NO_TOOL_DESC = "no_tool_desc"
    ALL_ABLATIONS = "all_ablations"


class PromptExperimentEnvironment(StrEnum):
    AIRLINE = "airline"
    RETAIL = "retail"


class PromptBundleInput(_ImmutablePromptContract):
    system_prompt: str
    wiki_rules: tuple[str, ...] = Field(min_length=1)

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("system_prompt must not be empty")
        return normalized_value

    @field_validator("wiki_rules")
    @classmethod
    def validate_wiki_rules(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized_rules = tuple(rule.strip() for rule in value)
        if any(not rule for rule in normalized_rules):
            raise ValueError("wiki_rules must not contain empty values")
        return normalized_rules


class PromptSuccessCriteria(_ImmutablePromptContract):
    require_final_response: bool = True
    exact_response: str | None = None
    required_response_substrings: tuple[str, ...] = ()
    forbidden_response_substrings: tuple[str, ...] = ()
    required_tool_names: tuple[str, ...] = ()
    forbidden_tool_names: tuple[str, ...] = ()

    @field_validator("exact_response")
    @classmethod
    def validate_exact_response(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("exact_response must not be empty")
        return normalized_value

    @field_validator(
        "required_response_substrings",
        "forbidden_response_substrings",
        "required_tool_names",
        "forbidden_tool_names",
    )
    @classmethod
    def validate_non_empty_values(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        normalized_values = tuple(item.strip() for item in value)
        if any(not item for item in normalized_values):
            raise ValueError("criteria values must not be empty")
        return normalized_values


class PromptTaskInput(_ImmutablePromptContract):
    task_id: str
    environment: PromptExperimentEnvironment
    instruction: str
    success_criteria: PromptSuccessCriteria = Field(
        default_factory=PromptSuccessCriteria
    )

    @field_validator("task_id", "instruction")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("must not be empty")
        return normalized_value


class PromptExperimentOptions(_ImmutablePromptContract):
    max_steps: int = Field(default=30, gt=0)
    seed: int = Field(default=0, ge=0)


class PromptExperimentRequest(_ImmutablePromptContract):
    prompt: PromptBundleInput
    task: PromptTaskInput
    variant: PromptExperimentVariant = PromptExperimentVariant.BASELINE
    options: PromptExperimentOptions = Field(
        default_factory=PromptExperimentOptions
    )


class PromptEvaluationSummary(_ImmutablePromptContract):
    reward: float = Field(ge=0, le=1)
    completed: bool
    criteria_total: int = Field(ge=0)
    criteria_passed: int = Field(ge=0)
    criteria_failed: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_criteria_counts(self) -> Self:
        if self.criteria_passed + self.criteria_failed != self.criteria_total:
            raise ValueError("evaluation criteria counts are inconsistent")
        return self


class PromptExperimentMetrics(_ImmutablePromptContract):
    step_count: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)


class PromptExperimentResult(_ImmutablePromptContract):
    task_id: str
    variant: PromptExperimentVariant
    final_response: str | None
    reward: float = Field(ge=0, le=1)
    completed: bool
    evaluation: PromptEvaluationSummary
    metrics: PromptExperimentMetrics

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("task_id must not be empty")
        return normalized_value

    @field_validator("final_response")
    @classmethod
    def validate_final_response(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("final_response must not be empty")
        return normalized_value

    @model_validator(mode="after")
    def validate_evaluation_summary(self) -> Self:
        if not isclose(self.reward, self.evaluation.reward):
            raise ValueError("reward is inconsistent with evaluation")
        if self.completed is not self.evaluation.completed:
            raise ValueError("completed is inconsistent with evaluation")
        return self
