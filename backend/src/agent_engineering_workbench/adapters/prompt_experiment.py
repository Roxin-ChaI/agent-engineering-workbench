from collections.abc import Mapping
from math import isclose
from typing import Protocol

from prompt_engineering_workbench import (  # type: ignore[import-untyped]
    ConfigurationError as PublicConfigurationError,
)
from prompt_engineering_workbench import (
    EnvironmentName as PublicEnvironmentName,
)
from prompt_engineering_workbench import (
    EvaluationContractError as PublicEvaluationContractError,
)
from prompt_engineering_workbench import (
    ExperimentConfig as PublicExperimentConfig,
)
from prompt_engineering_workbench import (
    ExperimentOrchestrationError as PublicExperimentOrchestrationError,
)
from prompt_engineering_workbench import (
    ExperimentResult as PublicExperimentResult,
)
from prompt_engineering_workbench import (
    ExperimentValidationError as PublicExperimentValidationError,
)
from prompt_engineering_workbench import (
    ExperimentVariant as PublicExperimentVariant,
)
from prompt_engineering_workbench import MessageRole as PublicMessageRole
from prompt_engineering_workbench import (
    ModelClientError as PublicModelClientError,
)
from prompt_engineering_workbench import PromptBundle as PublicPromptBundle
from prompt_engineering_workbench import (
    PromptEngineeringWorkbenchError as PublicPromptExperimentError,
)
from prompt_engineering_workbench import (
    PromptExperimentRunnerClosedError as PublicRunnerClosedError,
)
from prompt_engineering_workbench import (
    TaskDefinition as PublicTaskDefinition,
)
from prompt_engineering_workbench import (
    TaskEvaluatorError as PublicTaskEvaluatorError,
)
from prompt_engineering_workbench import (
    TaskSuccessCriteria as PublicTaskSuccessCriteria,
)
from pydantic import ValidationError

from agent_engineering_workbench.prompt_contracts import (
    PromptEvaluationSummary,
    PromptExperimentEnvironment,
    PromptExperimentMetrics,
    PromptExperimentRequest,
    PromptExperimentResult,
    PromptExperimentVariant,
    PromptSuccessCriteria,
)
from agent_engineering_workbench.prompt_errors import (
    InvalidPromptExperimentInputError,
    PromptExperimentConfigurationError,
    PromptExperimentEvaluationError,
    PromptExperimentExecutionError,
    PromptExperimentLifecycleError,
    PromptExperimentModelError,
    PromptExperimentProtocolError,
)

_EVALUATION_TYPE = "deterministic_constraint_satisfaction"

_VARIANTS = {
    PromptExperimentVariant.BASELINE: PublicExperimentVariant.BASELINE,
    PromptExperimentVariant.TONE_TRUMP: PublicExperimentVariant.TONE_TRUMP,
    PromptExperimentVariant.TONE_CASUAL: PublicExperimentVariant.TONE_CASUAL,
    PromptExperimentVariant.WIKI_RANDOM: PublicExperimentVariant.WIKI_RANDOM,
    PromptExperimentVariant.NO_TOOL_DESC: PublicExperimentVariant.NO_TOOL_DESC,
    PromptExperimentVariant.ALL_ABLATIONS: (PublicExperimentVariant.ALL_ABLATIONS),
}

_ENVIRONMENTS = {
    PromptExperimentEnvironment.AIRLINE: PublicEnvironmentName.AIRLINE,
    PromptExperimentEnvironment.RETAIL: PublicEnvironmentName.RETAIL,
}


class PromptExperimentRunnerProtocol(Protocol):
    """Public runner behavior required by the Workbench prompt adapter."""

    def run(
        self,
        *,
        bundle: PublicPromptBundle,
        task: PublicTaskDefinition,
        config: PublicExperimentConfig,
    ) -> PublicExperimentResult: ...


class PromptExperimentAdapter:
    """Translate Workbench prompt contracts through one injected public runner."""

    def __init__(self, runner: PromptExperimentRunnerProtocol) -> None:
        self._runner = runner

    def run(
        self,
        request: PromptExperimentRequest,
    ) -> PromptExperimentResult:
        if request.task.success_criteria.required_tool_names:
            raise InvalidPromptExperimentInputError(
                "Required tool criteria are unavailable in this workspace."
            )

        try:
            bundle = PublicPromptBundle(
                system_prompt=request.prompt.system_prompt,
                wiki_rules=request.prompt.wiki_rules,
                tools=(),
            )
            criteria = self._map_success_criteria(request.task.success_criteria)
            environment = _ENVIRONMENTS[request.task.environment]
            variant = _VARIANTS[request.variant]
            task = PublicTaskDefinition(
                task_id=request.task.task_id,
                environment=environment,
                instruction=request.task.instruction,
                success_criteria=criteria,
            )
            config = PublicExperimentConfig(
                experiment_id=request.task.task_id,
                variant=variant,
                environment=environment,
                task_ids=[request.task.task_id],
                max_steps=request.options.max_steps,
                seed=request.options.seed,
                concurrency=1,
            )
        except (ValidationError, ValueError) as exc:
            raise InvalidPromptExperimentInputError(
                "Prompt experiment input is invalid."
            ) from exc

        try:
            result = self._runner.run(
                bundle=bundle,
                task=task,
                config=config,
            )
        except PublicExperimentValidationError as exc:
            raise InvalidPromptExperimentInputError(
                "Prompt experiment input is invalid."
            ) from exc
        except PublicConfigurationError as exc:
            raise PromptExperimentConfigurationError(
                "Prompt experiment runner is not configured."
            ) from exc
        except PublicModelClientError as exc:
            raise PromptExperimentModelError(
                "Prompt experiment model request failed."
            ) from exc
        except (
            PublicEvaluationContractError,
            PublicTaskEvaluatorError,
        ) as exc:
            raise PromptExperimentEvaluationError(
                "Prompt experiment evaluation failed."
            ) from exc
        except PublicRunnerClosedError as exc:
            raise PromptExperimentLifecycleError(
                "Prompt experiment runner is unavailable."
            ) from exc
        except PublicExperimentOrchestrationError as exc:
            raise PromptExperimentExecutionError(
                "Prompt experiment execution failed."
            ) from exc
        except PublicPromptExperimentError as exc:
            raise PromptExperimentExecutionError(
                "Prompt experiment execution failed."
            ) from exc
        except Exception as exc:
            raise PromptExperimentExecutionError(
                "Prompt experiment execution failed."
            ) from exc

        try:
            return self._map_result(
                result=result,
                request=request,
                expected_environment=environment,
                expected_variant=variant,
            )
        except PromptExperimentProtocolError:
            raise
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an incompatible result."
            ) from exc

    @staticmethod
    def _map_success_criteria(
        criteria: PromptSuccessCriteria,
    ) -> PublicTaskSuccessCriteria:
        return PublicTaskSuccessCriteria(
            require_final_response=criteria.require_final_response,
            exact_response=criteria.exact_response,
            required_response_substrings=(criteria.required_response_substrings),
            forbidden_response_substrings=(criteria.forbidden_response_substrings),
            required_tool_names=criteria.required_tool_names,
            forbidden_tool_names=criteria.forbidden_tool_names,
        )

    @classmethod
    def _map_result(
        cls,
        *,
        result: PublicExperimentResult,
        request: PromptExperimentRequest,
        expected_environment: PublicEnvironmentName,
        expected_variant: PublicExperimentVariant,
    ) -> PromptExperimentResult:
        if not isinstance(result, PublicExperimentResult):
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an incompatible result."
            )
        if result.experiment_id != request.task.task_id:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an unexpected experiment."
            )
        if result.task_id != request.task.task_id:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an unexpected task."
            )
        if result.variant is not expected_variant:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an unexpected variant."
            )
        if result.environment is not expected_environment:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an unexpected environment."
            )

        final_response = cls._extract_final_response(result)
        evaluation = cls._map_evaluation(result, request.task.success_criteria)
        return PromptExperimentResult(
            task_id=result.task_id,
            variant=request.variant,
            final_response=final_response,
            reward=result.reward,
            completed=result.completed,
            evaluation=evaluation,
            metrics=PromptExperimentMetrics(
                step_count=len(result.steps),
                tool_call_count=sum(len(step.tool_calls) for step in result.steps),
            ),
        )

    @staticmethod
    def _extract_final_response(result: PublicExperimentResult) -> str:
        for step in reversed(result.steps):
            for message in reversed(step.messages):
                if (
                    message.role is PublicMessageRole.ASSISTANT
                    and not message.tool_calls
                    and message.content is not None
                    and message.content.strip()
                ):
                    return message.content
        raise PromptExperimentProtocolError(
            "Prompt experiment result has no final assistant response."
        )

    @classmethod
    def _map_evaluation(
        cls,
        result: PublicExperimentResult,
        criteria: PromptSuccessCriteria,
    ) -> PromptEvaluationSummary:
        evaluation = result.metadata.get("evaluation")
        if not isinstance(evaluation, Mapping):
            raise PromptExperimentProtocolError(
                "Prompt experiment result has no deterministic evaluation."
            )
        if evaluation.get("evaluation_type") != _EVALUATION_TYPE:
            raise PromptExperimentProtocolError(
                "Prompt experiment returned an unknown evaluation type."
            )

        total = cls._read_count(evaluation, "criteria_total")
        passed = cls._read_count(evaluation, "criteria_passed")
        failed = cls._read_count(evaluation, "criteria_failed")
        if passed + failed != total:
            raise PromptExperimentProtocolError(
                "Prompt experiment evaluation counts are inconsistent."
            )
        if total != cls._expected_criteria_count(criteria):
            raise PromptExperimentProtocolError(
                "Prompt experiment evaluation criteria do not match the request."
            )

        expected_completed = failed == 0
        expected_reward = 1.0 if expected_completed else 0.0
        if result.completed is not expected_completed or not isclose(
            result.reward, expected_reward
        ):
            raise PromptExperimentProtocolError(
                "Prompt experiment evaluation outcome is inconsistent."
            )

        return PromptEvaluationSummary(
            reward=result.reward,
            completed=result.completed,
            criteria_total=total,
            criteria_passed=passed,
            criteria_failed=failed,
        )

    @staticmethod
    def _read_count(evaluation: Mapping[object, object], field: str) -> int:
        value = evaluation.get(field)
        if type(value) is not int or value < 0:
            raise PromptExperimentProtocolError(
                "Prompt experiment evaluation counts are invalid."
            )
        return value

    @staticmethod
    def _expected_criteria_count(criteria: PromptSuccessCriteria) -> int:
        return (
            int(criteria.require_final_response)
            + int(criteria.exact_response is not None)
            + len(criteria.required_response_substrings)
            + len(criteria.forbidden_response_substrings)
            + len(criteria.required_tool_names)
            + len(criteria.forbidden_tool_names)
        )
