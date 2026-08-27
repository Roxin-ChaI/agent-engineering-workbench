import inspect
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import pytest
from fastapi.testclient import TestClient

import agent_engineering_workbench.app as production_app_module
from agent_engineering_workbench import dependencies, dev_server
from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.adapters.cwc import CWCAdapter
from agent_engineering_workbench.app import app
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)
from agent_engineering_workbench.contracts import RunResult, RunStatus
from agent_engineering_workbench.dependencies import (
    get_context_compression_adapter,
    get_github_review_adapter,
    get_knowledge_research_adapter,
    get_prompt_experiment_adapter,
    get_resume_optimizer_adapter,
    get_web_research_adapter,
)
from agent_engineering_workbench.dev_server import (
    FakeContextCompressionAdapter,
    FakeGitHubReviewAdapter,
    FakeKnowledgeResearchAdapter,
    FakePromptExperimentAdapter,
    FakeResumeOptimizerAdapter,
    FakeWebResearchAdapter,
    get_fake_context_compression_adapter,
    get_fake_github_review_adapter,
    get_fake_knowledge_research_adapter,
    get_fake_prompt_experiment_adapter,
    get_fake_resume_optimizer_adapter,
    get_fake_web_research_adapter,
)
from agent_engineering_workbench.github_review_contracts import (
    GitHubReviewAssessment,
    GitHubReviewResult,
    GitHubReviewSeverity,
)
from agent_engineering_workbench.github_review_errors import (
    GitHubReviewerClosedError,
)
from agent_engineering_workbench.prompt_contracts import (
    PromptExperimentRequest,
    PromptExperimentResult,
    PromptExperimentVariant,
)
from agent_engineering_workbench.resume_contracts import (
    ResumeAssessmentStatus,
    ResumeMatchRating,
    ResumeOptimizationResult,
    ResumeSectionType,
)
from agent_engineering_workbench.resume_errors import (
    ResumeOptimizerClosedError,
)

SUCCESS_PR_URL = "https://github.com/example/repository/pull/42"
EMPTY_FINDINGS_PR_URL = "https://github.com/example/repository/pull/43"
ERROR_PR_URL = "https://github.com/example/repository/pull/500"
RESUME_CONTENT = b"deterministic fake resume document"
RESUME_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
NORMAL_RESUME_JOB_DESCRIPTION = (
    "Backend engineer requiring Python, REST API, SQL, and automated testing."
)
WARNINGS_RESUME_JOB_DESCRIPTION = "FAKE_CASE_WARNINGS"
ERROR_RESUME_JOB_DESCRIPTION = "FAKE_CASE_UPSTREAM_ERROR"


class ResponseLike(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> dict[str, object]: ...


@pytest.fixture(autouse=True)
def configure_fake_dependency() -> Iterator[None]:
    app.dependency_overrides[get_web_research_adapter] = (
        get_fake_web_research_adapter
    )
    app.dependency_overrides[get_knowledge_research_adapter] = (
        get_fake_knowledge_research_adapter
    )
    app.dependency_overrides[get_context_compression_adapter] = (
        get_fake_context_compression_adapter
    )
    app.dependency_overrides[get_github_review_adapter] = (
        get_fake_github_review_adapter
    )
    app.dependency_overrides[get_resume_optimizer_adapter] = (
        get_fake_resume_optimizer_adapter
    )
    app.dependency_overrides[get_prompt_experiment_adapter] = (
        get_fake_prompt_experiment_adapter
    )
    yield
    app.dependency_overrides.clear()


def run_adapter(adapter: WorkbenchAdapter, query: str) -> RunResult:
    return adapter.run(query)


def parse_sse_event_types(body: str) -> list[str]:
    return [
        block.splitlines()[0].removeprefix("event: ")
        for block in body.strip().split("\n\n")
    ]


def prompt_request(
    *,
    variant: PromptExperimentVariant = PromptExperimentVariant.BASELINE,
    exact_response: str | None = None,
    required_response_substrings: tuple[str, ...] = (),
    forbidden_response_substrings: tuple[str, ...] = (),
    required_tool_names: tuple[str, ...] = (),
    forbidden_tool_names: tuple[str, ...] = (),
) -> PromptExperimentRequest:
    return PromptExperimentRequest.model_validate(
        {
            "prompt": {
                "system_prompt": "Follow the supplied policy exactly.",
                "wiki_rules": ["Confirm details before answering."],
            },
            "task": {
                "task_id": "fake-prompt-task",
                "environment": "airline",
                "instruction": "Confirm the baggage allowance.",
                "success_criteria": {
                    "require_final_response": True,
                    "exact_response": exact_response,
                    "required_response_substrings": (
                        required_response_substrings
                    ),
                    "forbidden_response_substrings": (
                        forbidden_response_substrings
                    ),
                    "required_tool_names": required_tool_names,
                    "forbidden_tool_names": forbidden_tool_names,
                },
            },
            "variant": variant,
            "options": {"max_steps": 30, "seed": 0},
        }
    )


def test_fake_adapter_satisfies_contract_and_returns_gui_fixture() -> None:
    result = run_adapter(FakeWebResearchAdapter(), "  local research question  ")

    assert result.status is RunStatus.COMPLETED
    assert result.output is not None
    assert "local research question" in result.output
    assert [event.name for event in result.trace] == [
        "question_received",
        "web_search",
        "final_answer",
    ]
    assert result.metrics.model_dump() == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 125.0,
    }
    assert [source.model_dump() for source in result.sources] == [
        {
            "title": "Fake Research Source One",
            "url": "https://example.com/fake-source-one",
        },
        {
            "title": "Fake Research Source Two",
            "url": "https://example.com/fake-source-two",
        },
    ]
    assert result.error is None


def test_dev_app_overrides_production_dependencies() -> None:
    assert app.dependency_overrides[get_web_research_adapter] is (
        get_fake_web_research_adapter
    )
    assert app.dependency_overrides[get_knowledge_research_adapter] is (
        get_fake_knowledge_research_adapter
    )
    assert app.dependency_overrides[get_context_compression_adapter] is (
        get_fake_context_compression_adapter
    )
    assert app.dependency_overrides[get_github_review_adapter] is (
        get_fake_github_review_adapter
    )
    assert app.dependency_overrides[get_resume_optimizer_adapter] is (
        get_fake_resume_optimizer_adapter
    )
    assert app.dependency_overrides[get_prompt_experiment_adapter] is (
        get_fake_prompt_experiment_adapter
    )


def test_rest_endpoint_returns_fake_result() -> None:
    response = TestClient(app).post(
        "/api/research/web",
        json={"query": "  REST integration check  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "REST integration check" in payload["output"]
    assert [trace["name"] for trace in payload["trace"]] == [
        "question_received",
        "web_search",
        "final_answer",
    ]
    assert payload["metrics"] == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 125.0,
    }
    assert len(payload["sources"]) == 2


def test_sse_endpoint_replays_fake_result() -> None:
    response = TestClient(app).post(
        "/api/research/web/stream",
        json={"query": "SSE integration check"},
    )

    assert response.status_code == 200
    assert parse_sse_event_types(response.text) == [
        "started",
        "trace",
        "trace",
        "trace",
        "completed",
    ]
    blocks = response.text.strip().split("\n\n")
    terminal_payload = json.loads(
        blocks[-1].splitlines()[1].removeprefix("data: ")
    )
    assert terminal_payload["data"]["status"] == "completed"
    assert "SSE integration check" in terminal_payload["data"]["output"]


def test_fake_knowledge_adapter_returns_pkra_shaped_gui_fixture() -> None:
    result = run_adapter(
        FakeKnowledgeResearchAdapter(),
        "  indexed knowledge question  ",
    )

    assert result.status is RunStatus.COMPLETED
    assert result.output is not None
    assert "indexed knowledge question" in result.output
    assert result.metrics.model_dump() == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 140.0,
    }
    assert result.trace == ()
    assert result.sources == ()
    assert result.error is None


def test_knowledge_rest_endpoint_returns_fake_result_without_real_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "_load_pkra_public_api",
        lambda: pytest.fail("production PKRA runner must not be created"),
    )

    response = TestClient(app).post(
        "/api/research/knowledge",
        json={"query": "  Knowledge REST integration check  "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "Knowledge REST integration check" in payload["output"]
    assert payload["metrics"] == {
        "iterations": 2,
        "tool_calls": 1,
        "duration_ms": 140.0,
    }
    assert payload["trace"] == []
    assert payload["sources"] == []


def test_knowledge_sse_endpoint_returns_started_then_completed() -> None:
    response = TestClient(app).post(
        "/api/research/knowledge/stream",
        json={"query": "Knowledge SSE integration check"},
    )

    assert response.status_code == 200
    assert parse_sse_event_types(response.text) == ["started", "completed"]
    blocks = response.text.strip().split("\n\n")
    terminal_payload = json.loads(
        blocks[-1].splitlines()[1].removeprefix("data: ")
    )
    assert terminal_payload["data"]["status"] == "completed"
    assert terminal_payload["data"]["trace"] == []
    assert terminal_payload["data"]["sources"] == []
    assert "Knowledge SSE integration check" in terminal_payload["data"]["output"]


def context_input(
    strategy: ContextCompressionStrategy = ContextCompressionStrategy.TRUNCATION,
) -> ContextCompressionInput:
    return ContextCompressionInput(
        messages=(
            ContextMessage(role="system", content="Keep this instruction."),
            ContextMessage(role="user", content="First question"),
            ContextMessage(role="assistant", content="First answer"),
            ContextMessage(role="user", content="Latest question"),
        ),
        target_token_budget=80,
        max_token_budget=120,
        strategy=strategy,
    )


@pytest.mark.parametrize("strategy", tuple(ContextCompressionStrategy))
def test_context_rest_endpoint_returns_deterministic_fake_result(
    strategy: ContextCompressionStrategy,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        CWCAdapter,
        "compress",
        lambda *_args, **_kwargs: pytest.fail("real CWC must not be called"),
    )
    compression_input = context_input(strategy)

    response = TestClient(app).post(
        "/api/context/compress",
        json=compression_input.model_dump(mode="json"),
    )

    assert response.status_code == 200
    result = ContextCompressionResult.model_validate(response.json())
    assert result.original_messages == compression_input.messages
    assert result.strategy is strategy
    assert result.duration_ms == 3.0
    if strategy is ContextCompressionStrategy.NO_COMPRESSION:
        assert result.compressed_messages == compression_input.messages
        assert result.original_token_estimate == 120
        assert result.compressed_token_estimate == 120
        assert result.tokens_saved_estimate == 0
        assert result.compression_ratio == 1.0
        assert result.compression_applied is False
    else:
        assert result.compressed_messages == (
            ContextMessage(
                role="assistant",
                content="Local fake context summary generated for GUI integration.",
            ),
            compression_input.messages[-1],
        )
        assert result.original_token_estimate == 120
        assert result.compressed_token_estimate == 48
        assert result.tokens_saved_estimate == 72
        assert result.compression_ratio == 0.4
        assert result.compression_applied is True


def test_fake_context_adapter_does_not_modify_input() -> None:
    compression_input = context_input()
    snapshot = compression_input.model_copy(deep=True)

    result = FakeContextCompressionAdapter().compress(compression_input)

    assert compression_input == snapshot
    assert result.original_messages == snapshot.messages


def test_production_context_dependency_remains_real_without_dev_override() -> None:
    app.dependency_overrides.pop(get_context_compression_adapter)

    adapter = get_context_compression_adapter()

    assert isinstance(adapter, CWCAdapter)
    assert get_context_compression_adapter not in app.dependency_overrides


def test_fake_prompt_adapter_returns_deterministic_contract_result() -> None:
    request = prompt_request(
        exact_response="Prompt Experiment exact result.",
        required_response_substrings=("Prompt Experiment",),
        forbidden_response_substrings=("unwanted",),
        forbidden_tool_names=("lookup_booking",),
    )
    adapter = FakePromptExperimentAdapter()

    first_result = adapter.run(request)
    second_result = adapter.run(request)

    assert first_result == second_result
    assert first_result.task_id == request.task.task_id
    assert first_result.variant is request.variant
    assert first_result.final_response == "Prompt Experiment exact result."
    assert first_result.reward == 1.0
    assert first_result.completed is True
    assert first_result.evaluation.model_dump() == {
        "reward": 1.0,
        "completed": True,
        "criteria_total": 5,
        "criteria_passed": 5,
        "criteria_failed": 0,
    }
    assert first_result.metrics.model_dump() == {
        "step_count": 1,
        "tool_call_count": 0,
    }


def test_prompt_rest_endpoint_returns_fake_result_without_api_key_or_factory(
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
    request = prompt_request(
        required_response_substrings=("deterministic response",),
        forbidden_response_substrings=("unwanted",),
    )

    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    result = PromptExperimentResult.model_validate(response.json())
    assert result.task_id == request.task.task_id
    assert result.variant is request.variant
    assert result.final_response is not None
    assert "Prompt Experiment" in result.final_response
    assert "deterministic response" in result.final_response
    assert result.reward == 1.0
    assert result.completed is True
    assert result.evaluation.criteria_total == 3
    assert result.evaluation.criteria_passed == 3
    assert result.evaluation.criteria_failed == 0
    assert result.metrics.step_count == 1
    assert result.metrics.tool_call_count == 0


def test_prompt_fake_failed_evaluation_remains_http_200() -> None:
    request = prompt_request(
        forbidden_response_substrings=("Prompt Experiment",),
    )

    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    result = PromptExperimentResult.model_validate(response.json())
    assert result.reward == 0.0
    assert result.completed is False
    assert result.evaluation.criteria_total == 2
    assert result.evaluation.criteria_passed == 1
    assert result.evaluation.criteria_failed == 1


@pytest.mark.parametrize("variant", tuple(PromptExperimentVariant))
def test_prompt_fake_supports_each_single_variant(
    variant: PromptExperimentVariant,
) -> None:
    request = prompt_request(variant=variant)

    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    result = PromptExperimentResult.model_validate(response.json())
    assert result.variant is variant


def test_prompt_fake_required_tools_fail_closed_without_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "create_prompt_experiment_runner",
        lambda *_args, **_kwargs: pytest.fail(
            "production prompt runner must not be created"
        ),
    )
    request = prompt_request(required_tool_names=("lookup_booking",))

    response = TestClient(app).post(
        "/api/prompts/experiment",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Prompt experiment input is invalid."
    }


def test_fake_prompt_adapter_has_no_external_execution_capability() -> None:
    source = inspect.getsource(FakePromptExperimentAdapter)

    assert all(
        forbidden not in source
        for forbidden in (
            "prompt_engineering_workbench",
            "create_prompt_experiment_runner",
            "DEEPSEEK_API_KEY",
            "httpx",
            "requests",
            "subprocess",
        )
    )


def test_production_app_does_not_enable_fake_prompt_experiments() -> None:
    app.dependency_overrides.pop(get_prompt_experiment_adapter)

    production_source = inspect.getsource(production_app_module)
    production_dependency_source = inspect.getsource(
        dependencies.get_prompt_experiment_adapter
    )

    assert get_prompt_experiment_adapter not in app.dependency_overrides
    assert "dev_server" not in production_source
    assert "FakePromptExperimentAdapter" not in production_source
    assert "create_prompt_experiment_runner" in production_dependency_source


def test_github_review_endpoint_returns_deterministic_fake_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "create_reviewer",
        lambda *_args, **_kwargs: pytest.fail(
            "production Reviewer runner must not be created"
        ),
    )

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": SUCCESS_PR_URL},
    )

    assert response.status_code == 200
    result = GitHubReviewResult.model_validate(response.json())
    assert result.target.model_dump() == {
        "owner": "example",
        "repository": "repository",
        "pull_number": 42,
    }
    assert result.pull_request.model_dump() == {
        "title": "Fix context handling in review pipeline",
        "state": "open",
        "author": "example-user",
        "base_branch": "main",
        "head_branch": "fix/context-handling",
        "created_at": "2026-01-10T09:00:00Z",
        "updated_at": "2026-01-12T15:30:00Z",
        "changed_files": 2,
        "additions": 28,
        "deletions": 7,
        "commits": 2,
    }
    assert "improves context handling" in result.summary
    assert len(result.findings) == 2
    assert [finding.severity for finding in result.findings] == [
        GitHubReviewSeverity.MEDIUM,
        GitHubReviewSeverity.LOW,
    ]
    assert [finding.file_path for finding in result.findings] == [
        "src/reviewer/context.py",
        "tests/test_context.py",
    ]
    assert all(
        (
            finding.location
            and finding.issue
            and finding.evidence
            and finding.recommendation
        )
        for finding in result.findings
    )
    assert "integration test" in result.test_gaps
    assert "focused" in result.maintainability
    assert (
        result.assessment
        is GitHubReviewAssessment.APPROVE_WITH_MINOR_COMMENTS
    )
    assert "**Medium**" in result.markdown
    assert "**Low**" in result.markdown


def test_github_review_empty_findings_scenario_returns_success() -> None:
    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": EMPTY_FINDINGS_PR_URL},
    )

    assert response.status_code == 200
    result = GitHubReviewResult.model_validate(response.json())
    assert result.target.pull_number == 43
    assert result.findings == ()
    assert result.summary
    assert result.test_gaps
    assert result.maintainability
    assert result.assessment is GitHubReviewAssessment.APPROVE
    assert result.markdown


def test_github_review_error_scenario_returns_safe_502() -> None:
    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": ERROR_PR_URL},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Unable to generate the pull request review."
    }
    assert "Deterministic fake" not in response.text


def test_github_review_invalid_url_returns_422() -> None:
    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": "not-a-pull-request-url"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Enter a public GitHub Pull Request URL"
    }


def test_fake_github_review_adapter_close_is_idempotent() -> None:
    adapter = FakeGitHubReviewAdapter()

    adapter.close()
    adapter.close()

    with pytest.raises(GitHubReviewerClosedError, match="closed"):
        adapter.review(SUCCESS_PR_URL)


def test_fake_github_review_has_no_external_or_write_capability() -> None:
    source = inspect.getsource(FakeGitHubReviewAdapter)

    assert all(
        forbidden not in source
        for forbidden in (
            "ai_github_reviewer",
            "create_reviewer",
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "github_token",
            "DEEPSEEK_API_KEY",
            "httpx",
            "requests",
            "create_comment",
            "submit_review",
            "merge_pull_request",
        )
    )


def test_production_app_does_not_enable_fake_github_review() -> None:
    app.dependency_overrides.pop(get_github_review_adapter)

    production_source = inspect.getsource(production_app_module)

    assert get_github_review_adapter not in app.dependency_overrides
    assert "dev_server" not in production_source
    assert "get_fake_github_review_adapter" not in production_source


def post_fake_resume(
    *,
    filename: str = "sample-resume.docx",
    content_type: str = RESUME_CONTENT_TYPE,
    job_description: str = NORMAL_RESUME_JOB_DESCRIPTION,
) -> ResponseLike:
    return TestClient(app).post(
        "/api/resume/optimize",
        files={"resume": (filename, RESUME_CONTENT, content_type)},
        data={"job_description": job_description},
    )


def test_resume_endpoint_returns_complete_deterministic_fake_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "create_resume_optimizer",
        lambda *_args, **_kwargs: pytest.fail(
            "production Resume Optimizer runner must not be created"
        ),
    )

    response = post_fake_resume()

    assert response.status_code == 200
    payload = response.json()
    result = ResumeOptimizationResult.model_validate(payload)
    assert result.analysis.overall_rating is ResumeMatchRating.HIGH
    assert result.analysis.overall_evaluation
    assert [assessment.status for assessment in result.analysis.assessments] == [
        ResumeAssessmentStatus.WELL_SUPPORTED,
        ResumeAssessmentStatus.UNDERREPRESENTED,
        ResumeAssessmentStatus.UNSUPPORTED,
    ]
    assert len(result.analysis.main_issues) == 2
    assert len(result.analysis.section_suggestions) == 2
    assert result.analysis.keyword_suggestions == (
        "Python",
        "REST API",
        "SQL",
        "automated testing",
    )
    assert result.analysis.truthfulness_risks
    assert result.analysis.content_not_to_add
    assert [section.section_type for section in result.optimized_resume.sections] == [
        ResumeSectionType.SUMMARY,
        ResumeSectionType.EXPERIENCE,
    ]
    assert sum(len(section.items) for section in result.optimized_resume.sections) == 3
    assert result.optimized_resume.pending_user_inputs == ()
    assert result.optimized_resume.warnings == ()
    assert result.warnings == ()
    assert "output_paths" not in payload


def test_resume_warnings_scenario_returns_distinct_pending_and_warning_data() -> None:
    response = post_fake_resume(job_description=WARNINGS_RESUME_JOB_DESCRIPTION)

    assert response.status_code == 200
    result = ResumeOptimizationResult.model_validate(response.json())
    assert result.analysis.overall_rating is ResumeMatchRating.MEDIUM
    assert len(result.optimized_resume.pending_user_inputs) == 2
    assert len(result.optimized_resume.warnings) == 1
    assert len(result.warnings) == 1
    assert any(
        item.needs_review and item.review_note
        for section in result.optimized_resume.sections
        for item in section.items
    )


def test_resume_upstream_scenario_returns_safe_502_and_closes_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_adapters: list[FakeResumeOptimizerAdapter] = []
    original_close = FakeResumeOptimizerAdapter.close

    def recording_close(adapter: FakeResumeOptimizerAdapter) -> None:
        original_close(adapter)
        closed_adapters.append(adapter)

    monkeypatch.setattr(FakeResumeOptimizerAdapter, "close", recording_close)

    response = post_fake_resume(job_description=ERROR_RESUME_JOB_DESCRIPTION)

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Resume optimizer returned an unusable result."
    }
    assert "Deterministic fake" not in response.text
    assert "upstream" not in response.text.lower()
    assert len(closed_adapters) == 1


def test_resume_unsupported_format_uses_real_upload_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        FakeResumeOptimizerAdapter,
        "optimize",
        lambda *_args, **_kwargs: pytest.fail(
            "fake adapter must not receive unsupported uploads"
        ),
    )

    response = post_fake_resume(filename="resume.txt", content_type="text/plain")

    assert response.status_code == 415
    assert response.json() == {
        "detail": "Resume must be a PDF or DOCX file."
    }


def test_resume_dev_wiring_preserves_temp_cleanup_and_request_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called_paths: list[Path] = []
    path_exists_during_call: list[bool] = []
    closed_adapters: list[FakeResumeOptimizerAdapter] = []
    original_optimize = FakeResumeOptimizerAdapter.optimize
    original_close = FakeResumeOptimizerAdapter.close

    def recording_optimize(
        adapter: FakeResumeOptimizerAdapter,
        *,
        resume_path: Path,
        job_description: str,
    ) -> ResumeOptimizationResult:
        called_paths.append(resume_path)
        path_exists_during_call.append(resume_path.exists())
        return original_optimize(
            adapter,
            resume_path=resume_path,
            job_description=job_description,
        )

    def recording_close(adapter: FakeResumeOptimizerAdapter) -> None:
        original_close(adapter)
        closed_adapters.append(adapter)

    monkeypatch.setattr(FakeResumeOptimizerAdapter, "optimize", recording_optimize)
    monkeypatch.setattr(FakeResumeOptimizerAdapter, "close", recording_close)

    response = post_fake_resume(filename="candidate.pdf", content_type="application/pdf")

    assert response.status_code == 200
    assert len(called_paths) == 1
    assert called_paths[0].name == "resume.pdf"
    assert path_exists_during_call == [True]
    assert not called_paths[0].exists()
    assert len(closed_adapters) == 1
    with pytest.raises(ResumeOptimizerClosedError, match="closed"):
        closed_adapters[0].optimize(
            resume_path=called_paths[0],
            job_description=NORMAL_RESUME_JOB_DESCRIPTION,
        )


def test_fake_resume_adapter_close_is_idempotent() -> None:
    adapter = FakeResumeOptimizerAdapter()

    adapter.close()
    adapter.close()

    with pytest.raises(ResumeOptimizerClosedError, match="closed"):
        adapter.optimize(
            resume_path=Path("resume.docx"),
            job_description=NORMAL_RESUME_JOB_DESCRIPTION,
        )


def test_fake_resume_adapter_has_no_external_execution_capability() -> None:
    source = inspect.getsource(FakeResumeOptimizerAdapter)

    assert all(
        forbidden not in source
        for forbidden in (
            "ai_resume_optimizer",
            "create_resume_optimizer",
            "DEEPSEEK_API_KEY",
            "httpx",
            "requests",
            "subprocess",
        )
    )


def test_production_app_does_not_enable_fake_resume_optimization() -> None:
    app.dependency_overrides.pop(get_resume_optimizer_adapter)

    production_source = inspect.getsource(production_app_module)

    assert get_resume_optimizer_adapter not in app.dependency_overrides
    assert "dev_server" not in production_source
    assert "FakeResumeOptimizerAdapter" not in production_source
    assert "FAKE_CASE_" not in production_source


def test_main_uses_local_uvicorn_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_uvicorn_run(
        application: object,
        *,
        host: str,
        port: int,
        reload: bool,
    ) -> None:
        captured.update(
            application=application,
            host=host,
            port=port,
            reload=reload,
        )

    monkeypatch.setattr(dev_server.uvicorn, "run", fake_uvicorn_run)

    dev_server.main()

    assert captured == {
        "application": app,
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
    }
