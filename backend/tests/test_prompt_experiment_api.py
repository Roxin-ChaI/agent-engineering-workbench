import inspect
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import pytest
from fastapi.testclient import TestClient
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
    PromptBundle,
    TaskDefinition,
    TrajectoryStep,
)
from prompt_engineering_workbench import (
    ModelClientError as PublicModelClientError,
)

import agent_engineering_workbench.api.prompt as prompt_api
from agent_engineering_workbench import dependencies
from agent_engineering_workbench.adapters.prompt_experiment import (
    PromptExperimentAdapter,
)
from agent_engineering_workbench.app import app
from agent_engineering_workbench.config import Settings
from agent_engineering_workbench.dependencies import get_prompt_experiment_adapter
from agent_engineering_workbench.prompt_contracts import (
    PromptEvaluationSummary,
    PromptExperimentMetrics,
    PromptExperimentRequest,
    PromptExperimentResult,
    PromptExperimentVariant,
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


class ResponseLike(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> dict[str, object]: ...


def request_payload(
    *,
    variant: str = "baseline",
    required_tool_names: list[str] | None = None,
) -> dict[str, object]:
    return {
        "prompt": {
            "system_prompt": "Follow the supplied policy exactly.",
            "wiki_rules": ["Confirm details before answering."],
        },
        "task": {
            "task_id": "task-1",
            "environment": "airline",
            "instruction": "Confirm the baggage allowance.",
            "success_criteria": {
                "require_final_response": True,
                "exact_response": None,
                "required_response_substrings": [],
                "forbidden_response_substrings": [],
                "required_tool_names": required_tool_names or [],
                "forbidden_tool_names": [],
            },
        },
        "variant": variant,
        "options": {"max_steps": 30, "seed": 0},
    }


def workbench_result(*, successful: bool = True) -> PromptExperimentResult:
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
            criteria_total=1,
            criteria_passed=int(successful),
            criteria_failed=int(not successful),
        ),
        metrics=PromptExperimentMetrics(step_count=1, tool_call_count=0),
    )


def public_result() -> ExperimentResult:
    return ExperimentResult(
        experiment_id="task-1",
        variant=ExperimentVariant.BASELINE,
        environment=EnvironmentName.AIRLINE,
        task_id="task-1",
        reward=1.0,
        completed=True,
        steps=[
            TrajectoryStep(
                step_index=0,
                messages=[
                    ConversationMessage(
                        role=MessageRole.ASSISTANT,
                        content="Your baggage allowance is confirmed.",
                    )
                ],
                tool_calls=[],
            )
        ],
        metadata={
            "evaluation": {
                "evaluation_type": "deterministic_constraint_satisfaction",
                "criteria_total": 1,
                "criteria_passed": 1,
                "criteria_failed": 0,
            }
        },
    )


class FakePromptAdapter:
    def __init__(self, outcome: PromptExperimentResult | BaseException) -> None:
        self.outcome = outcome
        self.requests: list[PromptExperimentRequest] = []

    def run(self, request: PromptExperimentRequest) -> PromptExperimentResult:
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class FakePublicRunner:
    def __init__(
        self,
        outcome: ExperimentResult | BaseException,
        *,
        close_error: BaseException | None = None,
    ) -> None:
        self.outcome = outcome
        self.close_error = close_error
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
        return self.outcome

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


@dataclass(frozen=True, repr=False)
class FakePromptRunnerConfig:
    deepseek_api_key: str
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 60.0

    def __repr__(self) -> str:
        return (
            "FakePromptRunnerConfig(deepseek_api_key=<redacted>, "
            f"deepseek_model={self.deepseek_model!r}, "
            f"deepseek_timeout_seconds={self.deepseek_timeout_seconds!r})"
        )


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def install_fake_adapter(adapter: FakePromptAdapter | PromptExperimentAdapter) -> None:
    app.dependency_overrides[get_prompt_experiment_adapter] = lambda: adapter


def post_prompt(payload: dict[str, object] | None = None) -> ResponseLike:
    return TestClient(app, raise_server_exceptions=False).post(
        "/api/prompts/experiment",
        json=request_payload() if payload is None else payload,
    )


def install_public_factory(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runner: FakePublicRunner,
    settings: Settings | None = None,
) -> list[FakePromptRunnerConfig]:
    captured_configs: list[FakePromptRunnerConfig] = []

    def fake_factory(config: FakePromptRunnerConfig) -> FakePublicRunner:
        captured_configs.append(config)
        return runner

    monkeypatch.setattr(
        dependencies,
        "PromptExperimentRunnerConfig",
        FakePromptRunnerConfig,
    )
    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        fake_factory,
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: settings or Settings(deepseek_api_key="not-a-real-key"),
    )
    return captured_configs


def test_prompt_experiment_returns_complete_workbench_contract() -> None:
    adapter = FakePromptAdapter(workbench_result())
    install_fake_adapter(adapter)

    response = post_prompt()

    assert response.status_code == 200
    assert len(adapter.requests) == 1
    assert response.json() == workbench_result().model_dump(mode="json")


def test_failed_evaluation_is_a_successful_http_result() -> None:
    adapter = FakePromptAdapter(workbench_result(successful=False))
    install_fake_adapter(adapter)

    response = post_prompt()

    assert response.status_code == 200
    assert response.json()["reward"] == 0.0
    assert response.json()["completed"] is False
    assert response.json()["evaluation"] == {
        "reward": 0.0,
        "completed": False,
        "criteria_total": 1,
        "criteria_passed": 0,
        "criteria_failed": 1,
    }


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"prompt": {}, "task": {}},
        request_payload(variant="unknown"),
    ),
)
def test_invalid_http_shape_returns_standard_422(
    payload: dict[str, object],
) -> None:
    adapter = FakePromptAdapter(workbench_result())
    install_fake_adapter(adapter)

    response = post_prompt(payload)

    assert response.status_code == 422
    assert adapter.requests == []


def test_required_tools_fail_closed_without_runner_execution() -> None:
    runner = FakePublicRunner(public_result())
    install_fake_adapter(PromptExperimentAdapter(runner))

    response = post_prompt(
        request_payload(required_tool_names=["lookup_booking"])
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Prompt experiment input is invalid."}
    assert runner.calls == []


@pytest.mark.parametrize(
    ("adapter_error", "expected_status", "expected_detail"),
    (
        (
            InvalidPromptExperimentInputError("secret input"),
            422,
            "Prompt experiment input is invalid.",
        ),
        (
            PromptExperimentModelError("secret model"),
            502,
            "Prompt experiment model request failed.",
        ),
        (
            PromptExperimentEvaluationError("secret evaluation"),
            502,
            "Prompt experiment evaluation failed.",
        ),
        (
            PromptExperimentProtocolError("secret protocol"),
            502,
            "Prompt experiment returned an invalid result.",
        ),
        (
            PromptExperimentExecutionError("secret execution"),
            502,
            "Prompt experiment execution failed.",
        ),
        (
            PromptExperimentConfigurationError("secret config"),
            500,
            "Prompt experiment service is not configured.",
        ),
        (
            PromptExperimentLifecycleError("secret lifecycle"),
            500,
            "Prompt experiment service is unavailable.",
        ),
        (
            RuntimeError("secret unexpected"),
            500,
            "Prompt experiment failed during internal processing.",
        ),
    ),
)
def test_prompt_errors_return_safe_http_responses(
    adapter_error: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    adapter = FakePromptAdapter(adapter_error)
    install_fake_adapter(adapter)

    response = post_prompt()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert len(adapter.requests) == 1


@pytest.mark.parametrize(
    ("model_name", "timeout_seconds"),
    (
        ("deepseek-v4-flash", 60.0),
        ("configured-model", 19.5),
    ),
)
def test_production_request_uses_public_factory_once_and_closes_once(
    monkeypatch: pytest.MonkeyPatch,
    model_name: str,
    timeout_seconds: float,
) -> None:
    runner = FakePublicRunner(public_result())
    captured_configs = install_public_factory(
        monkeypatch,
        runner=runner,
        settings=Settings(
            deepseek_api_key="not-a-real-key",
            model_name=model_name,
            deepseek_timeout_seconds=timeout_seconds,
        ),
    )

    response = post_prompt()

    assert response.status_code == 200
    assert len(captured_configs) == 1
    assert captured_configs[0] == FakePromptRunnerConfig(
        deepseek_api_key="not-a-real-key",
        deepseek_model=model_name,
        deepseek_timeout_seconds=timeout_seconds,
    )
    assert "not-a-real-key" not in repr(captured_configs[0])
    assert len(runner.calls) == 1
    assert runner.calls[0][0].tools == ()
    assert runner.calls[0][2].variant is ExperimentVariant.BASELINE
    assert runner.close_calls == 1


@pytest.mark.parametrize(
    "runner_error",
    (
        PublicModelClientError("secret model detail"),
        RuntimeError("secret unexpected detail"),
    ),
)
def test_request_scoped_runner_closes_once_after_execution_error(
    monkeypatch: pytest.MonkeyPatch,
    runner_error: BaseException,
) -> None:
    runner = FakePublicRunner(runner_error)
    install_public_factory(monkeypatch, runner=runner)

    response = post_prompt()

    assert response.status_code == 502
    assert "secret" not in response.text
    assert len(runner.calls) == 1
    assert runner.close_calls == 1


def test_close_failure_returns_safe_500_without_second_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakePublicRunner(
        public_result(),
        close_error=PublicModelClientError("secret close detail"),
    )
    install_public_factory(monkeypatch, runner=runner)

    response = post_prompt()

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Prompt experiment service is unavailable."
    }
    assert "secret" not in response.text
    assert len(runner.calls) == 1
    assert runner.close_calls == 1


@pytest.mark.parametrize(
    "settings",
    (
        Settings(deepseek_api_key=None),
        Settings(deepseek_api_key="   "),
        Settings(model_provider="unsupported", deepseek_api_key="not-a-real-key"),
    ),
)
def test_missing_or_unsupported_provider_configuration_skips_factory(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    factory_calls = 0

    def forbidden_factory(_config: object) -> FakePublicRunner:
        nonlocal factory_calls
        factory_calls += 1
        raise AssertionError("factory must not be called")

    monkeypatch.setattr(dependencies, "get_settings", lambda: settings)
    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        forbidden_factory,
    )

    response = post_prompt()

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Prompt experiment service is not configured."
    }
    assert factory_calls == 0


@pytest.mark.parametrize(
    ("factory_error", "expected_status", "expected_detail"),
    (
        (
            PublicConfigurationError("secret configuration detail"),
            500,
            "Prompt experiment service is not configured.",
        ),
        (
            PublicModelClientError("secret model construction detail"),
            502,
            "Prompt experiment model request failed.",
        ),
    ),
)
def test_public_factory_errors_are_mapped_safely(
    monkeypatch: pytest.MonkeyPatch,
    factory_error: BaseException,
    expected_status: int,
    expected_detail: str,
) -> None:
    factory_calls = 0

    def failing_factory(_config: object) -> FakePublicRunner:
        nonlocal factory_calls
        factory_calls += 1
        raise factory_error

    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        failing_factory,
    )
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(deepseek_api_key="not-a-real-key"),
    )

    response = post_prompt()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert factory_calls == 1


def test_prompt_route_openapi_and_existing_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    operation = paths["/api/prompts/experiment"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PromptExperimentRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/PromptExperimentResult"}
    assert "/api/resume/optimize" in paths
    assert "/api/github/review" in paths
    assert "/api/context/compress" in paths
    assert "/api/research/web" in paths
    assert "/api/research/knowledge" in paths
    assert "/health" in paths


def test_prompt_api_and_wiring_use_only_public_provider_boundary() -> None:
    api_source = inspect.getsource(prompt_api)
    dependency_source = inspect.getsource(dependencies.get_prompt_experiment_adapter)
    combined_source = api_source + dependency_source

    assert "prompt_engineering_workbench" not in api_source
    assert "create_prompt_experiment_runner" in dependency_source
    assert all(
        forbidden not in combined_source.lower()
        for forbidden in (
            "deepseekmodelclient",
            "openai import",
            "prompt_deepseek_api_key",
            "subprocess",
            "prompt_engineering_workbench.",
        )
    )


def test_response_uses_workbench_contract_not_upstream_result() -> None:
    annotation = inspect.signature(prompt_api.run_prompt_experiment).return_annotation

    assert annotation is PromptExperimentResult
    assert not issubclass(PromptExperimentResult, ExperimentResult)
    assert PromptExperimentResult is not ExperimentResult
