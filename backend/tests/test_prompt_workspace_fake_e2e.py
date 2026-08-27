import inspect
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import agent_engineering_workbench.app as production_app_module
from agent_engineering_workbench import dependencies
from agent_engineering_workbench.app import app
from agent_engineering_workbench.dependencies import get_prompt_experiment_adapter
from agent_engineering_workbench.dev_server import (
    FakePromptExperimentAdapter,
    get_fake_prompt_experiment_adapter,
)
from agent_engineering_workbench.prompt_contracts import PromptExperimentResult

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROMPT_WORKSPACE_SOURCE = (
    REPOSITORY_ROOT
    / "frontend/src/components/prompt-experiment-workspace.tsx"
)
FRONTEND_API_SOURCE = REPOSITORY_ROOT / "frontend/src/lib/api.ts"
FRONTEND_CONTRACT_SOURCE = REPOSITORY_ROOT / "frontend/src/lib/contracts.ts"
I18N_SOURCE = REPOSITORY_ROOT / "frontend/src/lib/i18n.ts"
GLOBAL_STYLES_SOURCE = REPOSITORY_ROOT / "frontend/src/app/globals.css"


def prompt_payload(
    *,
    variant: str = "baseline",
    forbidden_response_substrings: list[str] | None = None,
    required_tool_names: list[str] | None = None,
) -> dict[str, object]:
    return {
        "prompt": {
            "system_prompt": "Follow the supplied policy exactly.",
            "wiki_rules": [
                "Confirm details before answering.",
                "Keep the result concise.",
            ],
        },
        "task": {
            "task_id": "prompt-fake-e2e-task",
            "environment": "airline",
            "instruction": "Confirm the baggage allowance.",
            "success_criteria": {
                "require_final_response": True,
                "exact_response": None,
                "required_response_substrings": [
                    "deterministic response",
                    "ordered phrase",
                ],
                "forbidden_response_substrings": (
                    forbidden_response_substrings or ["unwanted phrase"]
                ),
                "required_tool_names": required_tool_names or [],
                "forbidden_tool_names": ["delete_booking"],
            },
        },
        "variant": variant,
        "options": {"max_steps": 17, "seed": 9},
    }


@pytest.fixture(autouse=True)
def configure_prompt_fake_dependency() -> Iterator[None]:
    app.dependency_overrides[get_prompt_experiment_adapter] = (
        get_fake_prompt_experiment_adapter
    )
    yield
    app.dependency_overrides.clear()


def post_prompt(payload: dict[str, object]) -> PromptExperimentResult:
    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=payload,
    )
    assert response.status_code == 200
    return PromptExperimentResult.model_validate(response.json())


def test_prompt_workspace_fake_e2e_success_request_and_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        lambda *_args, **_kwargs: pytest.fail(
            "production prompt runner must not be created"
        ),
    )
    payload = prompt_payload()

    result = post_prompt(payload)

    assert result.task_id == "prompt-fake-e2e-task"
    assert result.variant.value == "baseline"
    assert result.final_response is not None
    assert "Prompt Experiment" in result.final_response
    assert "deterministic response ordered phrase" in result.final_response
    assert result.reward == 1.0
    assert result.completed is True
    assert result.evaluation.model_dump() == {
        "reward": 1.0,
        "completed": True,
        "criteria_total": 5,
        "criteria_passed": 5,
        "criteria_failed": 0,
    }
    assert result.metrics.model_dump() == {
        "step_count": 1,
        "tool_call_count": 0,
    }


def test_prompt_workspace_fake_e2e_failed_criteria_is_http_200() -> None:
    result = post_prompt(
        prompt_payload(
            forbidden_response_substrings=["Prompt Experiment"],
        )
    )

    assert result.final_response is not None
    assert result.reward == 0.0
    assert result.completed is False
    assert result.evaluation.criteria_failed == 1
    assert result.metrics.step_count == 1
    assert result.metrics.tool_call_count == 0


def test_prompt_workspace_fake_e2e_preserves_non_default_variant() -> None:
    payload = prompt_payload(variant="tone_casual")

    result = post_prompt(payload)

    assert payload["variant"] == "tone_casual"
    assert result.variant.value == "tone_casual"


def test_prompt_workspace_fake_e2e_backend_required_tools_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        lambda *_args, **_kwargs: pytest.fail(
            "production prompt runner must not be created"
        ),
    )

    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=prompt_payload(required_tool_names=["lookup_booking"]),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Prompt experiment input is invalid."
    }


def test_prompt_workspace_fake_e2e_frontend_request_and_single_call_boundary(
) -> None:
    workspace_source = PROMPT_WORKSPACE_SOURCE.read_text()
    api_source = FRONTEND_API_SOURCE.read_text()
    contract_source = FRONTEND_CONTRACT_SOURCE.read_text()

    assert '"/api/prompts/experiment"' in api_source
    assert '"Prompt experiment"' in api_source
    assert "request," in api_source
    assert workspace_source.count("await runPromptExperiment(request)") == 1
    assert all(
        field in workspace_source
        for field in (
            "system_prompt: normalizedSystemPrompt",
            "wiki_rules: normalizedWikiRules",
            "task_id: normalizedTaskId",
            "exact_response: exactResponse.trim() || null",
            "required_response_substrings: splitLines(requiredSubstrings)",
            "forbidden_response_substrings: splitLines(forbiddenSubstrings)",
            "required_tool_names: normalizedRequiredTools",
            "forbidden_tool_names: splitLines(forbiddenTools)",
            "max_steps: numericMaxSteps",
            "seed: numericSeed",
        )
    )
    assert all(
        field in contract_source
        for field in (
                "system_prompt: string",
                "wiki_rules: string[]",
                "exact_response?: string | null",
                "required_response_substrings?: string[]",
                "forbidden_response_substrings?: string[]",
                "required_tool_names?: string[]",
                "forbidden_tool_names?: string[]",
                "max_steps?: number",
                "seed?: number",
        )
    )
    assert not any(
        forbidden in workspace_source
        for forbidden in ("setTimeout", "setInterval", "retry", "poll")
    )


def test_prompt_workspace_fake_e2e_frontend_guards_before_request() -> None:
    source = PROMPT_WORKSPACE_SOURCE.read_text()
    request_call = source.index("await runPromptExperiment(request)")

    assert source.index("if (!normalizedSystemPrompt)") < request_call
    assert source.index("if (!normalizedInstruction)") < request_call
    tools_guard = source.index("if (normalizedRequiredTools.length > 0)")
    assert tools_guard < source.index('setError("toolsUnavailable")') < request_call
    assert source.index("inFlight.current = true") < request_call
    assert "disabled={loading}" in source
    assert 't("prompt.running")' in source


def test_prompt_workspace_placeholders_are_not_request_values() -> None:
    source = PROMPT_WORKSPACE_SOURCE.read_text()
    i18n_source = I18N_SOURCE.read_text()

    assert all(
        declaration in source
        for declaration in (
            'const [systemPrompt, setSystemPrompt] = useState("")',
            'const [wikiRules, setWikiRules] = useState("")',
            'const [taskId, setTaskId] = useState("")',
            'const [instruction, setInstruction] = useState("")',
        )
    )
    assert all(
        field in source
        for field in (
            "system_prompt: normalizedSystemPrompt",
            "wiki_rules: normalizedWikiRules",
            "task_id: normalizedTaskId",
            "instruction: normalizedInstruction",
            "required_response_substrings: splitLines(requiredSubstrings)",
            "forbidden_response_substrings: splitLines(forbiddenSubstrings)",
            "required_tool_names: normalizedRequiredTools",
            "forbidden_tool_names: splitLines(forbiddenTools)",
        )
    )
    assert "WORKBENCH_REAL_E2E" not in source
    assert "real-prompt-e2e" not in source
    assert all(
        i18n_source.count(f'"{key}"') == 2
        for key in (
            "prompt.systemPromptPlaceholder",
            "prompt.wikiRulesPlaceholder",
            "prompt.taskIdPlaceholder",
            "prompt.instructionPlaceholder",
            "prompt.exactResponsePlaceholder",
            "prompt.requiredSubstringsPlaceholder",
            "prompt.forbiddenSubstringsPlaceholder",
            "prompt.requiredToolsPlaceholder",
            "prompt.forbiddenToolsPlaceholder",
        )
    )


def test_prompt_workspace_placeholders_hide_on_focus() -> None:
    source = PROMPT_WORKSPACE_SOURCE.read_text()
    styles = GLOBAL_STYLES_SOURCE.read_text()

    assert source.count('className="prompt-placeholder ') == 6
    assert ".prompt-placeholder::placeholder" in styles
    assert ".prompt-placeholder:focus::placeholder" in styles
    assert "opacity: 0.65" in styles
    assert "opacity: 0" in styles


def test_prompt_workspace_fake_e2e_rendering_i18n_and_responsive_boundaries(
) -> None:
    source = PROMPT_WORKSPACE_SOURCE.read_text()
    i18n_source = I18N_SOURCE.read_text()

    assert all(
        field in source
        for field in (
            "result.final_response",
            "result.task_id",
            "result.variant",
            "result.reward",
            "result.completed",
            "result.evaluation.criteria_passed",
            "result.evaluation.criteria_total",
            "result.evaluation.criteria_failed",
            "result.metrics.step_count",
            "result.metrics.tool_call_count",
            'result.completed ? "status-completed" : "status-stopped"',
            '"prompt.evaluationFailed"',
        )
    )
    assert source.index("setResult(null)") < source.index(
        "await runPromptExperiment(request)"
    )
    assert all(
        i18n_source.count(f'"{key}"') == 2
        for key in (
            "prompt.title",
            "prompt.run",
            "prompt.result",
            "prompt.evaluation",
            "prompt.toolsUnavailable",
            "prompt.toolsUnavailableError",
        )
    )
    assert all(
        responsive_class in source
        for responsive_class in (
            "xl:grid-cols-2",
            "lg:grid-cols-2",
            "sm:grid-cols-3",
            "sm:flex-row",
            "sm:grid-cols-2 xl:grid-cols-4",
        )
    )
    assert all(
        shared_theme_class in source
        for shared_theme_class in (
            "panel",
            "workbench-input",
            "text-primary",
            "text-muted",
            "primary-action",
        )
    )


def test_prompt_workspace_fake_e2e_has_no_production_or_secret_leakage() -> None:
    fake_source = inspect.getsource(FakePromptExperimentAdapter)
    production_source = inspect.getsource(production_app_module)
    dependency_source = inspect.getsource(
        dependencies.get_prompt_experiment_adapter
    )

    assert "FakePromptExperimentAdapter" not in production_source
    assert "dev_server" not in production_source
    assert "create_prompt_experiment_runner" in dependency_source
    assert all(
        forbidden not in fake_source
        for forbidden in (
            "DEEPSEEK_API_KEY",
            "prompt_engineering_workbench",
            "create_prompt_experiment_runner",
            "httpx",
            "requests",
        )
    )
