import ast
import inspect
from typing import cast

import pytest
from prompt_engineering_workbench import (  # type: ignore[import-untyped]
    ConfigurationError as PublicConfigurationError,
)
from prompt_engineering_workbench import (
    ConversationMessage,
    EnvironmentName,
    ExperimentConfig,
    ExperimentResult,
    ExperimentVariant,
    MessageRole,
    ModelToolCall,
    PromptBundle,
    TaskDefinition,
    ToolCallRecord,
    TrajectoryStep,
)
from prompt_engineering_workbench import (
    EvaluationContractError as PublicEvaluationContractError,
)
from prompt_engineering_workbench import (
    ExperimentOrchestrationError as PublicExperimentOrchestrationError,
)
from prompt_engineering_workbench import (
    ExperimentValidationError as PublicExperimentValidationError,
)
from prompt_engineering_workbench import (
    ModelClientError as PublicModelClientError,
)
from prompt_engineering_workbench import (
    PromptExperimentRunnerClosedError as PublicRunnerClosedError,
)
from prompt_engineering_workbench import (
    TaskEvaluatorError as PublicTaskEvaluatorError,
)

import agent_engineering_workbench.adapters.prompt_experiment as adapter_module
from agent_engineering_workbench.adapters import PromptExperimentAdapter
from agent_engineering_workbench.prompt_contracts import (
    PromptBundleInput,
    PromptExperimentEnvironment,
    PromptExperimentOptions,
    PromptExperimentRequest,
    PromptExperimentVariant,
    PromptSuccessCriteria,
    PromptTaskInput,
)
from agent_engineering_workbench.prompt_errors import (
    InvalidPromptExperimentInputError,
    PromptExperimentConfigurationError,
    PromptExperimentError,
    PromptExperimentEvaluationError,
    PromptExperimentExecutionError,
    PromptExperimentLifecycleError,
    PromptExperimentModelError,
    PromptExperimentProtocolError,
)


def make_request(
    *,
    variant: PromptExperimentVariant = PromptExperimentVariant.BASELINE,
    criteria: PromptSuccessCriteria | None = None,
    options: PromptExperimentOptions | None = None,
) -> PromptExperimentRequest:
    return PromptExperimentRequest(
        prompt=PromptBundleInput(
            system_prompt="Follow the supplied policy exactly.",
            wiki_rules=("Confirm details before answering.",),
        ),
        task=PromptTaskInput(
            task_id="task-1",
            environment=PromptExperimentEnvironment.AIRLINE,
            instruction="Confirm the baggage allowance.",
            success_criteria=criteria or PromptSuccessCriteria(),
        ),
        variant=variant,
        options=options or PromptExperimentOptions(),
    )


def make_result(
    *,
    variant: ExperimentVariant = ExperimentVariant.BASELINE,
    task_id: str = "task-1",
    experiment_id: str = "task-1",
    environment: EnvironmentName = EnvironmentName.AIRLINE,
    reward: float = 1.0,
    completed: bool = True,
    criteria_total: int = 1,
    criteria_passed: int = 1,
    criteria_failed: int = 0,
    metadata: dict[str, object] | None = None,
    include_final_response: bool = True,
) -> ExperimentResult:
    model_tool_call = ModelToolCall(
        call_id="call-1",
        tool_name="lookup_booking",
        arguments_json='{"booking_id":"ABC"}',
    )
    tool_record = ToolCallRecord(
        call_id="call-1",
        tool_name="lookup_booking",
        arguments={"booking_id": "ABC"},
        result="confirmed",
        error=None,
    )
    steps = [
        TrajectoryStep(
            step_index=0,
            messages=[
                ConversationMessage(
                    role=MessageRole.ASSISTANT,
                    tool_calls=[model_tool_call],
                )
            ],
            tool_calls=[tool_record],
        )
    ]
    if include_final_response:
        steps.append(
            TrajectoryStep(
                step_index=1,
                messages=[
                    ConversationMessage(
                        role=MessageRole.ASSISTANT,
                        content="Your baggage allowance is confirmed.",
                    )
                ],
                tool_calls=[],
            )
        )
    return ExperimentResult(
        experiment_id=experiment_id,
        variant=variant,
        environment=environment,
        task_id=task_id,
        reward=reward,
        completed=completed,
        steps=steps,
        metadata=metadata
        or {
            "evaluation": {
                "evaluation_type": ("deterministic_constraint_satisfaction"),
                "criteria_total": criteria_total,
                "criteria_passed": criteria_passed,
                "criteria_failed": criteria_failed,
            }
        },
    )


class FakeRunner:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[tuple[PromptBundle, TaskDefinition, ExperimentConfig]] = []
        self.close_calls = 0

    def run(
        self,
        *,
        bundle: PromptBundle,
        task: TaskDefinition,
        config: ExperimentConfig,
    ) -> ExperimentResult:
        self.calls.append((bundle, task, config))
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return cast(ExperimentResult, self.outcome)

    def close(self) -> None:
        self.close_calls += 1


def test_adapter_maps_request_and_calls_runner_exactly_once() -> None:
    criteria = PromptSuccessCriteria(
        require_final_response=True,
        exact_response="Confirmed",
        required_response_substrings=("allowance", "confirmed"),
        forbidden_response_substrings=("unknown",),
        required_tool_names=(),
        forbidden_tool_names=("cancel_booking",),
    )
    request = make_request(
        variant=PromptExperimentVariant.TONE_CASUAL,
        criteria=criteria,
        options=PromptExperimentOptions(max_steps=9, seed=4),
    )
    runner = FakeRunner(
        make_result(
            variant=ExperimentVariant.TONE_CASUAL,
            criteria_total=6,
            criteria_passed=6,
        )
    )

    PromptExperimentAdapter(runner).run(request)

    assert len(runner.calls) == 1
    bundle, task, config = runner.calls[0]
    assert bundle.system_prompt == request.prompt.system_prompt
    assert bundle.wiki_rules == request.prompt.wiki_rules
    assert bundle.tools == ()
    assert task.task_id == request.task.task_id
    assert task.environment is EnvironmentName.AIRLINE
    assert task.instruction == request.task.instruction
    assert task.success_criteria is not None
    assert task.success_criteria.model_dump() == criteria.model_dump()
    assert config.experiment_id == request.task.task_id
    assert config.variant is ExperimentVariant.TONE_CASUAL
    assert config.environment is EnvironmentName.AIRLINE
    assert config.task_ids == [request.task.task_id]
    assert config.max_steps == 9
    assert config.seed == 4
    assert config.concurrency == 1
    assert runner.close_calls == 0


@pytest.mark.parametrize(
    ("workbench_variant", "public_variant"),
    (
        (PromptExperimentVariant.BASELINE, ExperimentVariant.BASELINE),
        (PromptExperimentVariant.TONE_TRUMP, ExperimentVariant.TONE_TRUMP),
        (PromptExperimentVariant.TONE_CASUAL, ExperimentVariant.TONE_CASUAL),
        (PromptExperimentVariant.WIKI_RANDOM, ExperimentVariant.WIKI_RANDOM),
        (PromptExperimentVariant.NO_TOOL_DESC, ExperimentVariant.NO_TOOL_DESC),
        (
            PromptExperimentVariant.ALL_ABLATIONS,
            ExperimentVariant.ALL_ABLATIONS,
        ),
    ),
)
def test_each_selected_variant_maps_to_one_runner_call(
    workbench_variant: PromptExperimentVariant,
    public_variant: ExperimentVariant,
) -> None:
    runner = FakeRunner(make_result(variant=public_variant))

    result = PromptExperimentAdapter(runner).run(
        make_request(variant=workbench_variant)
    )

    assert len(runner.calls) == 1
    assert runner.calls[0][2].variant is public_variant
    assert result.variant is workbench_variant


def test_success_result_maps_final_response_evaluation_and_metrics() -> None:
    runner = FakeRunner(make_result())

    result = PromptExperimentAdapter(runner).run(make_request())

    assert result.task_id == "task-1"
    assert result.variant is PromptExperimentVariant.BASELINE
    assert result.final_response == "Your baggage allowance is confirmed."
    assert result.reward == 1.0
    assert result.completed is True
    assert result.evaluation.model_dump() == {
        "reward": 1.0,
        "completed": True,
        "criteria_total": 1,
        "criteria_passed": 1,
        "criteria_failed": 0,
    }
    assert result.metrics.model_dump() == {
        "step_count": 2,
        "tool_call_count": 1,
    }
    assert runner.close_calls == 0


def test_failed_evaluation_returns_a_normal_structured_result() -> None:
    runner = FakeRunner(
        make_result(
            reward=0.0,
            completed=False,
            criteria_passed=0,
            criteria_failed=1,
        )
    )

    result = PromptExperimentAdapter(runner).run(make_request())

    assert result.reward == 0.0
    assert result.completed is False
    assert result.evaluation.criteria_passed == 0
    assert result.evaluation.criteria_failed == 1


def test_required_tool_criteria_fail_before_runner_execution() -> None:
    runner = FakeRunner(make_result())
    request = make_request(
        criteria=PromptSuccessCriteria(required_tool_names=("lookup_booking",))
    )

    with pytest.raises(InvalidPromptExperimentInputError, match="unavailable"):
        PromptExperimentAdapter(runner).run(request)

    assert runner.calls == []


def test_upstream_semantic_criteria_validation_maps_to_input_error() -> None:
    runner = FakeRunner(make_result())
    request = make_request(
        criteria=PromptSuccessCriteria(
            required_response_substrings=("same",),
            forbidden_response_substrings=("same",),
        )
    )

    with pytest.raises(InvalidPromptExperimentInputError) as captured:
        PromptExperimentAdapter(runner).run(request)

    assert runner.calls == []
    assert "same" not in str(captured.value)


@pytest.mark.parametrize("outcome", (None, [], [make_result(), make_result()]))
def test_non_single_public_result_fails_closed(outcome: object) -> None:
    runner = FakeRunner(outcome)

    with pytest.raises(PromptExperimentProtocolError, match="incompatible"):
        PromptExperimentAdapter(runner).run(make_request())

    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "result",
    (
        make_result(experiment_id="other-experiment"),
        make_result(task_id="other-task"),
        make_result(variant=ExperimentVariant.WIKI_RANDOM),
        make_result(environment=EnvironmentName.RETAIL),
    ),
)
def test_unexpected_result_identity_fails_closed(
    result: ExperimentResult,
) -> None:
    with pytest.raises(PromptExperimentProtocolError, match="unexpected"):
        PromptExperimentAdapter(FakeRunner(result)).run(make_request())


def test_missing_final_assistant_response_fails_closed() -> None:
    result = make_result(include_final_response=False)

    with pytest.raises(PromptExperimentProtocolError, match="final assistant"):
        PromptExperimentAdapter(FakeRunner(result)).run(make_request())


@pytest.mark.parametrize(
    "evaluation",
    (
        None,
        {},
        {"evaluation_type": "unknown"},
        {
            "evaluation_type": "deterministic_constraint_satisfaction",
            "criteria_total": True,
            "criteria_passed": 1,
            "criteria_failed": 0,
        },
        {
            "evaluation_type": "deterministic_constraint_satisfaction",
            "criteria_total": 1,
            "criteria_passed": 1,
            "criteria_failed": 1,
        },
        {
            "evaluation_type": "deterministic_constraint_satisfaction",
            "criteria_total": 2,
            "criteria_passed": 2,
            "criteria_failed": 0,
        },
    ),
)
def test_malformed_evaluation_metadata_fails_closed(
    evaluation: object,
) -> None:
    result = make_result(metadata={"evaluation": evaluation})

    with pytest.raises(PromptExperimentProtocolError):
        PromptExperimentAdapter(FakeRunner(result)).run(make_request())


@pytest.mark.parametrize(
    ("reward", "completed"),
    ((0.0, True), (1.0, False)),
)
def test_inconsistent_evaluation_outcome_fails_closed(
    reward: float,
    completed: bool,
) -> None:
    result = make_result(reward=reward, completed=completed)

    with pytest.raises(PromptExperimentProtocolError, match="outcome"):
        PromptExperimentAdapter(FakeRunner(result)).run(make_request())


@pytest.mark.parametrize(
    ("public_error", "workbench_error"),
    (
        (
            PublicExperimentValidationError("validation detail"),
            InvalidPromptExperimentInputError,
        ),
        (
            PublicConfigurationError("configuration detail"),
            PromptExperimentConfigurationError,
        ),
        (
            PublicModelClientError("provider secret detail"),
            PromptExperimentModelError,
        ),
        (
            PublicEvaluationContractError("evaluation detail"),
            PromptExperimentEvaluationError,
        ),
        (
            PublicTaskEvaluatorError("evaluation detail"),
            PromptExperimentEvaluationError,
        ),
        (
            PublicRunnerClosedError("closed detail"),
            PromptExperimentLifecycleError,
        ),
        (
            PublicExperimentOrchestrationError("orchestration detail"),
            PromptExperimentExecutionError,
        ),
        (RuntimeError("unexpected secret detail"), PromptExperimentExecutionError),
    ),
)
def test_public_and_unexpected_errors_map_to_safe_workbench_errors(
    public_error: BaseException,
    workbench_error: type[Exception],
) -> None:
    runner = FakeRunner(public_error)

    with pytest.raises(workbench_error) as captured:
        PromptExperimentAdapter(runner).run(make_request())

    assert len(runner.calls) == 1
    assert captured.value.__cause__ is public_error
    assert "detail" not in str(captured.value)


def test_prompt_errors_share_one_workbench_boundary() -> None:
    error_types = (
        InvalidPromptExperimentInputError,
        PromptExperimentConfigurationError,
        PromptExperimentModelError,
        PromptExperimentEvaluationError,
        PromptExperimentLifecycleError,
        PromptExperimentProtocolError,
        PromptExperimentExecutionError,
    )

    assert all(
        issubclass(error_type, PromptExperimentError) for error_type in error_types
    )


def test_adapter_imports_only_upstream_root_and_has_no_production_assembly() -> None:
    source = inspect.getsource(adapter_module)
    tree = ast.parse(source)
    upstream_imports = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("prompt_engineering_workbench")
    ]

    assert upstream_imports
    assert set(upstream_imports) == {"prompt_engineering_workbench"}
    assert "create_prompt_experiment_runner" not in source
    assert "deepseek" not in source.lower()
    assert "api_key" not in source.lower()
    assert "close(" not in inspect.getsource(PromptExperimentAdapter.run)
