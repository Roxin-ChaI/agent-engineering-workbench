"""Local-only FastAPI entry point backed by deterministic fake integration data."""

import re
from collections.abc import Iterator
from pathlib import Path

import uvicorn

from agent_engineering_workbench.adapter import WorkbenchAdapter
from agent_engineering_workbench.app import app
from agent_engineering_workbench.context_contracts import (
    ContextCompressionInput,
    ContextCompressionResult,
    ContextCompressionStrategy,
    ContextMessage,
)
from agent_engineering_workbench.contracts import (
    RunMetrics,
    RunResult,
    RunStatus,
    SourceReference,
    TraceEvent,
)
from agent_engineering_workbench.dependencies import (
    get_context_compression_adapter,
    get_github_review_adapter,
    get_knowledge_research_adapter,
    get_prompt_experiment_adapter,
    get_resume_optimizer_adapter,
    get_web_research_adapter,
)
from agent_engineering_workbench.github_review_contracts import (
    GitHubPullRequestMetadata,
    GitHubReviewAssessment,
    GitHubReviewFinding,
    GitHubReviewResult,
    GitHubReviewSeverity,
    GitHubReviewTarget,
)
from agent_engineering_workbench.github_review_errors import (
    GitHubReviewerClosedError,
    GitHubReviewExecutionError,
    InvalidGitHubPullRequestError,
)
from agent_engineering_workbench.prompt_contracts import (
    PromptEvaluationSummary,
    PromptExperimentMetrics,
    PromptExperimentRequest,
    PromptExperimentResult,
)
from agent_engineering_workbench.prompt_errors import (
    InvalidPromptExperimentInputError,
)
from agent_engineering_workbench.resume_contracts import (
    OptimizedResume,
    ResumeAssessmentStatus,
    ResumeMatchAnalysis,
    ResumeMatchRating,
    ResumeOptimizationItem,
    ResumeOptimizationResult,
    ResumeOptimizationSection,
    ResumeRequirementAssessment,
    ResumeSectionType,
)
from agent_engineering_workbench.resume_errors import (
    ResumeOptimizationUpstreamError,
    ResumeOptimizerClosedError,
)

_PUBLIC_PULL_REQUEST_URL = re.compile(
    r"https://github\.com/(?P<owner>[^/\s]+)/(?P<repository>[^/\s]+)/pull/"
    r"(?P<pull_number>[1-9]\d*)/?"
)


class FakeWebResearchAdapter:
    """Return deterministic data for local GUI integration without external calls."""

    def run(self, user_input: str) -> RunResult:
        query = user_input.strip()
        if not query:
            raise ValueError("user_input must not be empty")

        return RunResult(
            status=RunStatus.COMPLETED,
            output=(
                "Local Fake Web Research result for "
                f'"{query}". No external services were called.'
            ),
            trace=(
                TraceEvent(
                    sequence=0,
                    event_type="request",
                    name="question_received",
                    detail=f'Normalized local query: "{query}"',
                ),
                TraceEvent(
                    sequence=1,
                    event_type="tool_call",
                    name="web_search",
                    detail="Returned deterministic local search fixtures.",
                ),
                TraceEvent(
                    sequence=2,
                    event_type="answer",
                    name="final_answer",
                    detail="Produced the local Fake Web Research result.",
                ),
            ),
            metrics=RunMetrics(
                iterations=2,
                tool_calls=1,
                duration_ms=125.0,
            ),
            sources=(
                SourceReference(
                    title="Fake Research Source One",
                    url="https://example.com/fake-source-one",
                ),
                SourceReference(
                    title="Fake Research Source Two",
                    url="https://example.com/fake-source-two",
                ),
            ),
            error=None,
        )


class FakeKnowledgeResearchAdapter:
    """Return PKRA-shaped local data without database or external calls."""

    def run(self, user_input: str) -> RunResult:
        query = user_input.strip()
        if not query:
            raise ValueError("user_input must not be empty")

        return RunResult(
            status=RunStatus.COMPLETED,
            output=(
                "Local Fake Knowledge Research result for "
                f'"{query}". No external services were called.'
            ),
            trace=(),
            metrics=RunMetrics(
                iterations=2,
                tool_calls=1,
                duration_ms=140.0,
            ),
            sources=(),
            error=None,
        )


class FakeContextCompressionAdapter:
    """Return deterministic Context Lab data without invoking CWC."""

    def compress(
        self,
        compression_input: ContextCompressionInput,
    ) -> ContextCompressionResult:
        original_messages = compression_input.messages
        if not original_messages:
            return ContextCompressionResult(
                original_messages=(),
                compressed_messages=(),
                original_token_estimate=0,
                compressed_token_estimate=0,
                tokens_saved_estimate=0,
                compression_ratio=1.0,
                strategy=compression_input.strategy,
                duration_ms=3.0,
                compression_applied=False,
                compressed_message_count=0,
                preserved_message_count=0,
            )

        if (
            compression_input.strategy
            is ContextCompressionStrategy.NO_COMPRESSION
        ):
            return ContextCompressionResult(
                original_messages=original_messages,
                compressed_messages=original_messages,
                original_token_estimate=120,
                compressed_token_estimate=120,
                tokens_saved_estimate=0,
                compression_ratio=1.0,
                strategy=compression_input.strategy,
                duration_ms=3.0,
                compression_applied=False,
                compressed_message_count=0,
                preserved_message_count=len(original_messages),
            )

        return ContextCompressionResult(
            original_messages=original_messages,
            compressed_messages=(
                ContextMessage(
                    role="assistant",
                    content=(
                        "Local fake context summary generated for GUI "
                        "integration."
                    ),
                ),
                original_messages[-1],
            ),
            original_token_estimate=120,
            compressed_token_estimate=48,
            tokens_saved_estimate=72,
            compression_ratio=0.4,
            strategy=compression_input.strategy,
            duration_ms=3.0,
            compression_applied=True,
            compressed_message_count=max(len(original_messages) - 1, 0),
            preserved_message_count=1,
        )


class FakeGitHubReviewAdapter:
    """Return deterministic, read-only GitHub Review data without I/O."""

    def __init__(self) -> None:
        self._closed = False

    def review(self, pull_request_url: str) -> GitHubReviewResult:
        if self._closed:
            raise GitHubReviewerClosedError(
                "Fake GitHub review adapter is closed"
            )

        match = _PUBLIC_PULL_REQUEST_URL.fullmatch(pull_request_url)
        if match is None:
            raise InvalidGitHubPullRequestError(
                "Enter a public GitHub Pull Request URL"
            )

        pull_number = int(match.group("pull_number"))
        if pull_number == 500:
            raise GitHubReviewExecutionError(
                "Deterministic fake review execution failure"
            )

        target = GitHubReviewTarget(
            owner=match.group("owner"),
            repository=match.group("repository"),
            pull_number=pull_number,
        )
        pull_request = GitHubPullRequestMetadata(
            title="Fix context handling in review pipeline",
            state="open",
            author="example-user",
            base_branch="main",
            head_branch="fix/context-handling",
            created_at="2026-01-10T09:00:00Z",
            updated_at="2026-01-12T15:30:00Z",
            changed_files=2,
            additions=28,
            deletions=7,
            commits=2,
        )

        if pull_number == 43:
            return GitHubReviewResult(
                target=target,
                pull_request=pull_request,
                summary=(
                    "The context handling update is focused and no findings "
                    "were identified in this deterministic review."
                ),
                findings=(),
                test_gaps="No additional test gaps were identified.",
                maintainability=(
                    "The change keeps context handling isolated and readable."
                ),
                assessment=GitHubReviewAssessment.APPROVE,
                markdown=(
                    "# Pull Request Review\n\n"
                    "No findings were reported for the context handling "
                    "update.\n\n"
                    "**Assessment:** Approve\n"
                ),
            )

        findings = (
            GitHubReviewFinding(
                severity=GitHubReviewSeverity.MEDIUM,
                file_path="src/reviewer/context.py",
                location="lines 42-48",
                issue=(
                    "The context limit is applied after the review payload "
                    "is assembled."
                ),
                evidence=(
                    "The payload can exceed the configured limit before the "
                    "final truncation step runs."
                ),
                recommendation=(
                    "Apply the context limit while assembling the review "
                    "payload."
                ),
            ),
            GitHubReviewFinding(
                severity=GitHubReviewSeverity.LOW,
                file_path="tests/test_context.py",
                location="lines 18-26",
                issue="The boundary case at the exact context limit is absent.",
                evidence=(
                    "Current cases cover values below and above the limit but "
                    "not an equal value."
                ),
                recommendation=(
                    "Add a deterministic test for a payload exactly at the "
                    "configured limit."
                ),
            ),
        )
        return GitHubReviewResult(
            target=target,
            pull_request=pull_request,
            summary=(
                "This Pull Request improves context handling in the review "
                "pipeline while keeping the change focused."
            ),
            findings=findings,
            test_gaps=(
                "Add an integration test covering context limits across the "
                "full review pipeline."
            ),
            maintainability=(
                "The change is focused and keeps context handling logic "
                "isolated."
            ),
            assessment=GitHubReviewAssessment.APPROVE_WITH_MINOR_COMMENTS,
            markdown=(
                "# Pull Request Review\n\n"
                "The context handling update is focused.\n\n"
                "## Findings\n"
                "1. **Medium** — Apply the context limit during payload "
                "assembly.\n"
                "2. **Low** — Add the exact-limit boundary test.\n\n"
                "**Assessment:** Approve with minor comments\n"
            ),
        )

    def close(self) -> None:
        self._closed = True


class FakeResumeOptimizerAdapter:
    """Return deterministic Resume Optimization data without external calls."""

    def __init__(self) -> None:
        self._closed = False

    def optimize(
        self,
        *,
        resume_path: Path,
        job_description: str,
    ) -> ResumeOptimizationResult:
        if self._closed:
            raise ResumeOptimizerClosedError(
                "Fake resume optimizer adapter is closed."
            )
        if "FAKE_CASE_UPSTREAM_ERROR" in job_description:
            raise ResumeOptimizationUpstreamError(
                "Deterministic fake resume optimizer upstream failure."
            )

        include_warnings = "FAKE_CASE_WARNINGS" in job_description
        return _fake_resume_optimization_result(
            resume_suffix=resume_path.suffix,
            include_warnings=include_warnings,
        )

    def close(self) -> None:
        self._closed = True


class FakePromptExperimentAdapter:
    """Return deterministic Prompt Experiment data without external calls."""

    def run(
        self,
        request: PromptExperimentRequest,
    ) -> PromptExperimentResult:
        criteria = request.task.success_criteria
        if criteria.required_tool_names:
            raise InvalidPromptExperimentInputError(
                "Required tool criteria are unavailable in this workspace."
            )

        final_response = criteria.exact_response
        if final_response is None:
            required_text = " ".join(criteria.required_response_substrings)
            final_response = "Prompt Experiment completed with a local result."
            if required_text:
                final_response = f"{final_response} {required_text}"

        checks = [
            *([bool(final_response)] if criteria.require_final_response else []),
            *(
                [final_response == criteria.exact_response]
                if criteria.exact_response is not None
                else []
            ),
            *(
                value in final_response
                for value in criteria.required_response_substrings
            ),
            *(
                value not in final_response
                for value in criteria.forbidden_response_substrings
            ),
            *(True for _value in criteria.forbidden_tool_names),
        ]
        criteria_passed = sum(checks)
        criteria_total = len(checks)
        criteria_failed = criteria_total - criteria_passed
        completed = criteria_failed == 0
        reward = 1.0 if completed else 0.0

        return PromptExperimentResult(
            task_id=request.task.task_id,
            variant=request.variant,
            final_response=final_response,
            reward=reward,
            completed=completed,
            evaluation=PromptEvaluationSummary(
                reward=reward,
                completed=completed,
                criteria_total=criteria_total,
                criteria_passed=criteria_passed,
                criteria_failed=criteria_failed,
            ),
            metrics=PromptExperimentMetrics(
                step_count=1,
                tool_call_count=0,
            ),
        )


def _fake_resume_optimization_result(
    *,
    resume_suffix: str,
    include_warnings: bool,
) -> ResumeOptimizationResult:
    pending_user_inputs = (
        (
            "Provide a verified request-volume metric for the API project.",
            "Confirm whether the candidate owned the database migration.",
        )
        if include_warnings
        else ()
    )
    optimized_warnings = (
        (
            "A project responsibility remains pending candidate confirmation.",
        )
        if include_warnings
        else ()
    )
    result_warnings = (
        (
            "The source resume did not provide a verified scale metric.",
        )
        if include_warnings
        else ()
    )

    return ResumeOptimizationResult(
        analysis=ResumeMatchAnalysis(
            overall_rating=(
                ResumeMatchRating.MEDIUM
                if include_warnings
                else ResumeMatchRating.HIGH
            ),
            overall_evaluation=(
                "Candidate demonstrates solid backend engineering fundamentals "
                "but should make API ownership and measurable testing impact "
                f"more explicit. The local fake input used {resume_suffix}."
            ),
            assessments=(
                ResumeRequirementAssessment(
                    requirement_id="python-backend",
                    status=ResumeAssessmentStatus.WELL_SUPPORTED,
                    source_block_ids=("experience-1", "skills-1"),
                    reason=(
                        "The resume directly describes production Python API "
                        "development."
                    ),
                    suggested_action=(
                        "Keep the Python ownership evidence near the top of "
                        "the experience section."
                    ),
                ),
                ResumeRequirementAssessment(
                    requirement_id="automated-testing",
                    status=ResumeAssessmentStatus.UNDERREPRESENTED,
                    source_block_ids=("experience-1",),
                    reason=(
                        "Automated testing is mentioned without measurable "
                        "impact or scope."
                    ),
                    suggested_action=(
                        "Add a verified outcome from the existing test work."
                    ),
                ),
                ResumeRequirementAssessment(
                    requirement_id="cloud-operations",
                    status=ResumeAssessmentStatus.UNSUPPORTED,
                    source_block_ids=(),
                    reason=(
                        "The source resume does not provide cloud operations "
                        "evidence."
                    ),
                    suggested_action=(
                        "Do not add cloud operations claims without candidate "
                        "confirmation."
                    ),
                ),
            ),
            main_issues=(
                "API ownership is described without a verified scale metric.",
                "Testing impact is less visible than implementation work.",
            ),
            section_suggestions=(
                "Lead the experience section with Python REST API ownership.",
                "Group verified SQL and automated testing evidence together.",
            ),
            keyword_suggestions=(
                "Python",
                "REST API",
                "SQL",
                "automated testing",
            ),
            truthfulness_risks=(
                "Do not infer request volume or team size from the source.",
            ),
            content_not_to_add=(
                "Unverified cloud platform ownership.",
            ),
        ),
        optimized_resume=OptimizedResume(
            sections=(
                ResumeOptimizationSection(
                    section_type=ResumeSectionType.SUMMARY,
                    title="Professional Summary",
                    items=(
                        ResumeOptimizationItem(
                            text=(
                                "Backend engineer experienced in Python, REST "
                                "APIs, SQL, and automated testing."
                            ),
                            source_block_ids=("summary-1", "skills-1"),
                            related_requirement_ids=(
                                "python-backend",
                                "automated-testing",
                            ),
                            needs_review=False,
                            review_note=None,
                        ),
                    ),
                    source_block_ids=("summary-1", "skills-1"),
                ),
                ResumeOptimizationSection(
                    section_type=ResumeSectionType.EXPERIENCE,
                    title="Experience",
                    items=(
                        ResumeOptimizationItem(
                            text=(
                                "Owned Python REST API implementation and SQL "
                                "integration for a backend service."
                            ),
                            source_block_ids=("experience-1",),
                            related_requirement_ids=("python-backend",),
                            needs_review=False,
                            review_note=None,
                        ),
                        ResumeOptimizationItem(
                            text=(
                                "Expanded automated tests for critical API "
                                "behavior."
                            ),
                            source_block_ids=("experience-1",),
                            related_requirement_ids=("automated-testing",),
                            needs_review=include_warnings,
                            review_note=(
                                "Add a verified impact metric before using this "
                                "item."
                                if include_warnings
                                else None
                            ),
                        ),
                    ),
                    source_block_ids=("experience-1",),
                ),
            ),
            pending_user_inputs=pending_user_inputs,
            warnings=optimized_warnings,
        ),
        warnings=result_warnings,
    )


def get_fake_web_research_adapter() -> WorkbenchAdapter:
    return FakeWebResearchAdapter()


def get_fake_knowledge_research_adapter() -> WorkbenchAdapter:
    return FakeKnowledgeResearchAdapter()


def get_fake_context_compression_adapter() -> FakeContextCompressionAdapter:
    return FakeContextCompressionAdapter()


def get_fake_github_review_adapter() -> FakeGitHubReviewAdapter:
    return FakeGitHubReviewAdapter()


def get_fake_resume_optimizer_adapter() -> Iterator[FakeResumeOptimizerAdapter]:
    adapter = FakeResumeOptimizerAdapter()
    try:
        yield adapter
    finally:
        adapter.close()


def get_fake_prompt_experiment_adapter() -> FakePromptExperimentAdapter:
    return FakePromptExperimentAdapter()


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


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
