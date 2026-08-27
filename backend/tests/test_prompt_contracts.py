import inspect

import pytest
from prompt_engineering_workbench import (  # type: ignore[import-untyped]
    ExperimentConfig,
    ExperimentResult,
    ExperimentVariant,
    PromptBundle,
    TaskDefinition,
    TaskEvaluation,
    TaskSuccessCriteria,
)
from pydantic import ValidationError

from agent_engineering_workbench import prompt_contracts
from agent_engineering_workbench.prompt_contracts import (
    PromptBundleInput,
    PromptEvaluationSummary,
    PromptExperimentEnvironment,
    PromptExperimentMetrics,
    PromptExperimentOptions,
    PromptExperimentRequest,
    PromptExperimentResult,
    PromptExperimentVariant,
    PromptSuccessCriteria,
    PromptTaskInput,
)


def make_request() -> PromptExperimentRequest:
    return PromptExperimentRequest(
        prompt=PromptBundleInput(
            system_prompt="You are a concise airline assistant.",
            wiki_rules=("Follow airline policy.",),
        ),
        task=PromptTaskInput(
            task_id="task-1",
            environment=PromptExperimentEnvironment.AIRLINE,
            instruction="Confirm the baggage allowance.",
        ),
    )


def make_result(*, successful: bool = True) -> PromptExperimentResult:
    reward = 1.0 if successful else 0.0
    return PromptExperimentResult(
        task_id="task-1",
        variant=PromptExperimentVariant.BASELINE,
        final_response="Your baggage allowance is confirmed.",
        reward=reward,
        completed=successful,
        evaluation=PromptEvaluationSummary(
            reward=reward,
            completed=successful,
            criteria_total=2,
            criteria_passed=2 if successful else 1,
            criteria_failed=0 if successful else 1,
        ),
        metrics=PromptExperimentMetrics(
            step_count=1,
            tool_call_count=0,
        ),
    )


def test_minimal_request_uses_stable_defaults() -> None:
    request = make_request()

    assert request.variant is PromptExperimentVariant.BASELINE
    assert request.options == PromptExperimentOptions(max_steps=30, seed=0)
    assert request.task.success_criteria == PromptSuccessCriteria()


def test_request_supports_all_success_criteria_fields() -> None:
    criteria = PromptSuccessCriteria(
        require_final_response=False,
        exact_response="Confirmed",
        required_response_substrings=("confirm",),
        forbidden_response_substrings=("unknown",),
        required_tool_names=("lookup_booking",),
        forbidden_tool_names=("cancel_booking",),
    )

    assert criteria.model_dump(mode="json") == {
        "require_final_response": False,
        "exact_response": "Confirmed",
        "required_response_substrings": ["confirm"],
        "forbidden_response_substrings": ["unknown"],
        "required_tool_names": ["lookup_booking"],
        "forbidden_tool_names": ["cancel_booking"],
    }


@pytest.mark.parametrize("variant", tuple(PromptExperimentVariant))
def test_all_six_variants_are_valid(variant: PromptExperimentVariant) -> None:
    request = make_request().model_copy(update={"variant": variant})

    assert PromptExperimentRequest.model_validate(request.model_dump()).variant is variant


def test_supported_variants_match_upstream_public_contract() -> None:
    assert {variant.value for variant in PromptExperimentVariant} == {
        variant.value for variant in ExperimentVariant
    }
    assert len(PromptExperimentVariant) == 6


def test_unknown_variant_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PromptExperimentRequest.model_validate(
            {**make_request().model_dump(), "variant": "unknown"}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (("system_prompt", "  "), ("instruction", "\t")),
)
def test_required_prompt_and_task_text_must_not_be_blank(
    field: str, value: str
) -> None:
    payload = make_request().model_dump()
    if field == "system_prompt":
        payload["prompt"][field] = value
    else:
        payload["task"][field] = value

    with pytest.raises(ValidationError, match="must not be empty"):
        PromptExperimentRequest.model_validate(payload)


def test_request_rejects_empty_wiki_rules() -> None:
    payload = make_request().model_dump()
    payload["prompt"]["wiki_rules"] = []

    with pytest.raises(ValidationError):
        PromptExperimentRequest.model_validate(payload)


def test_request_json_round_trip_preserves_contract() -> None:
    request = PromptExperimentRequest(
        prompt=make_request().prompt,
        task=make_request().task,
        variant=PromptExperimentVariant.WIKI_RANDOM,
        options=PromptExperimentOptions(max_steps=12, seed=7),
    )

    assert PromptExperimentRequest.model_validate_json(request.model_dump_json()) == request


@pytest.mark.parametrize(
    "options",
    (
        {"max_steps": 0, "seed": 0},
        {"max_steps": 1, "seed": -1},
    ),
)
def test_experiment_options_reject_invalid_numeric_bounds(
    options: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        PromptExperimentOptions.model_validate(options)


def test_request_contract_excludes_provider_secrets_and_sdk_configuration() -> None:
    schema = PromptExperimentRequest.model_json_schema()
    schema_text = str(schema).lower()

    assert "api_key" not in schema_text
    assert "deepseek" not in schema_text
    assert "base_url" not in schema_text
    assert "model_client" not in schema_text


@pytest.mark.parametrize("successful", (True, False))
def test_result_serializes_success_and_failed_evaluations(
    successful: bool,
) -> None:
    result = make_result(successful=successful)

    serialized = result.model_dump(mode="json")
    assert serialized["task_id"] == "task-1"
    assert serialized["variant"] == "baseline"
    assert serialized["final_response"] == (
        "Your baggage allowance is confirmed."
    )
    assert serialized["reward"] == (1.0 if successful else 0.0)
    assert serialized["completed"] is successful
    assert serialized["evaluation"]["criteria_total"] == 2
    assert serialized["evaluation"]["criteria_failed"] == (
        0 if successful else 1
    )
    assert serialized["metrics"] == {
        "step_count": 1,
        "tool_call_count": 0,
    }
    assert PromptExperimentResult.model_validate(serialized) == result


def test_result_allows_missing_final_response_for_incomplete_trajectory() -> None:
    result = make_result(successful=False).model_copy(
        update={"final_response": None}
    )

    assert PromptExperimentResult.model_validate(result.model_dump()).final_response is None


def test_evaluation_summary_rejects_inconsistent_criteria_counts() -> None:
    with pytest.raises(ValidationError, match="criteria counts"):
        PromptEvaluationSummary(
            reward=0.0,
            completed=False,
            criteria_total=2,
            criteria_passed=2,
            criteria_failed=1,
        )


@pytest.mark.parametrize("field", ("reward", "completed"))
def test_result_rejects_evaluation_summary_mismatch(field: str) -> None:
    payload = make_result().model_dump()
    payload["evaluation"][field] = 0.0 if field == "reward" else False

    with pytest.raises(ValidationError, match=f"{field} is inconsistent"):
        PromptExperimentResult.model_validate(payload)


def test_workbench_contracts_do_not_inherit_upstream_models() -> None:
    pairs = (
        (PromptBundleInput, PromptBundle),
        (PromptTaskInput, TaskDefinition),
        (PromptSuccessCriteria, TaskSuccessCriteria),
        (PromptExperimentOptions, ExperimentConfig),
        (PromptExperimentResult, ExperimentResult),
        (PromptEvaluationSummary, TaskEvaluation),
    )

    assert all(not issubclass(workbench, upstream) for workbench, upstream in pairs)
    assert "prompt_engineering_workbench" not in inspect.getsource(prompt_contracts)


def test_prompt_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        PromptExperimentRequest.model_validate(
            {**make_request().model_dump(), "deepseek_api_key": "secret"}
        )
