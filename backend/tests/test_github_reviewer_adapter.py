import inspect
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest
from ai_github_reviewer import (  # type: ignore[import-untyped]
    GitHubRetrievalError as ReviewerGitHubRetrievalError,
)
from ai_github_reviewer import (  # type: ignore[import-untyped]
    InvalidPullRequestURLError as ReviewerInvalidPullRequestURLError,
)
from ai_github_reviewer import (  # type: ignore[import-untyped]
    ModelReviewError as ReviewerModelReviewError,
)
from ai_github_reviewer import (  # type: ignore[import-untyped]
    ReviewerClosedError as PublicReviewerClosedError,
)
from ai_github_reviewer import (  # type: ignore[import-untyped]
    ReviewerConfigurationError as PublicReviewerConfigurationError,
)
from ai_github_reviewer import (  # type: ignore[import-untyped]
    ReviewProtocolError as ReviewerReviewProtocolError,
)

import agent_engineering_workbench.adapters.github_reviewer as adapter_module
from agent_engineering_workbench.adapters import GitHubReviewerAdapter
from agent_engineering_workbench.adapters.github_reviewer import (
    ReviewerResultLike,
)
from agent_engineering_workbench.github_review_contracts import (
    GitHubReviewAssessment,
    GitHubReviewSeverity,
)
from agent_engineering_workbench.github_review_errors import (
    GitHubReviewConfigurationError,
    GitHubReviewerClosedError,
    GitHubReviewExecutionError,
    GitHubReviewProtocolError,
    GitHubReviewRetrievalError,
    InvalidGitHubPullRequestError,
)

URL = "https://github.com/owner/repository/pull/123"


@dataclass(frozen=True)
class FakeTarget:
    owner: str = "owner"
    repository: str = "repository"
    pull_number: int = 123


@dataclass(frozen=True)
class FakePullRequest:
    title: str = "Controlled change"
    state: str = "open"
    author: str = "reviewer"
    base_branch: str = "main"
    head_branch: str = "feature"
    created_at: str = "2026-01-01T00:00:00Z"
    updated_at: str = "2026-01-02T00:00:00Z"
    changed_files: int = 2
    additions: int = 4
    deletions: int = 1
    commits: int = 3


@dataclass(frozen=True)
class FakeFinding:
    severity: str
    file_path: str
    location: str
    issue: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class FakeReviewResult:
    target: FakeTarget
    pull_request: FakePullRequest
    summary: str
    findings: tuple[FakeFinding, ...]
    test_gaps: str
    maintainability: str
    assessment: str
    markdown: str


def make_result(
    *,
    findings: tuple[FakeFinding, ...] = (
        FakeFinding(
            severity="High",
            file_path="src/first.py",
            location="line 10",
            issue="First issue.",
            evidence="First evidence.",
            recommendation="First recommendation.",
        ),
        FakeFinding(
            severity="Low",
            file_path="src/second.py",
            location="file-level",
            issue="Second issue.",
            evidence="Second evidence.",
            recommendation="Second recommendation.",
        ),
    ),
    assessment: str = "Request changes",
) -> FakeReviewResult:
    return FakeReviewResult(
        target=FakeTarget(),
        pull_request=FakePullRequest(),
        summary="Controlled summary.",
        findings=findings,
        test_gaps="Controlled test gap.",
        maintainability="Controlled maintainability note.",
        assessment=assessment,
        markdown="# Pull Request Review\n",
    )


class FakeRunner:
    def __init__(
        self,
        outcome: ReviewerResultLike | BaseException,
    ) -> None:
        self.outcome = outcome
        self.urls: list[str] = []
        self.close_calls = 0

    def review(self, pull_request_url: str) -> ReviewerResultLike:
        self.urls.append(pull_request_url)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome

    def close(self) -> None:
        self.close_calls += 1


def test_review_maps_complete_result_without_modifying_input() -> None:
    external_result = make_result()
    snapshot = deepcopy(external_result)
    runner = FakeRunner(external_result)
    url_snapshot = deepcopy(URL)

    result = GitHubReviewerAdapter(runner).review(URL)

    assert runner.urls == [URL]
    assert URL == url_snapshot
    assert external_result == snapshot
    assert result.target.model_dump() == {
        "owner": "owner",
        "repository": "repository",
        "pull_number": 123,
    }
    assert result.pull_request.model_dump() == {
        "title": "Controlled change",
        "state": "open",
        "author": "reviewer",
        "base_branch": "main",
        "head_branch": "feature",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "changed_files": 2,
        "additions": 4,
        "deletions": 1,
        "commits": 3,
    }
    assert result.summary == "Controlled summary."
    assert result.test_gaps == "Controlled test gap."
    assert result.maintainability == "Controlled maintainability note."
    assert result.assessment is GitHubReviewAssessment.REQUEST_CHANGES
    assert result.markdown == "# Pull Request Review\n"


def test_findings_preserve_order_and_all_public_fields() -> None:
    result = GitHubReviewerAdapter(FakeRunner(make_result())).review(URL)

    assert [finding.severity for finding in result.findings] == [
        GitHubReviewSeverity.HIGH,
        GitHubReviewSeverity.LOW,
    ]
    assert [finding.file_path for finding in result.findings] == [
        "src/first.py",
        "src/second.py",
    ]
    assert result.findings[0].model_dump() == {
        "severity": GitHubReviewSeverity.HIGH,
        "file_path": "src/first.py",
        "location": "line 10",
        "issue": "First issue.",
        "evidence": "First evidence.",
        "recommendation": "First recommendation.",
    }


def test_empty_findings_are_supported() -> None:
    result = GitHubReviewerAdapter(
        FakeRunner(make_result(findings=()))
    ).review(URL)

    assert result.findings == ()


@pytest.mark.parametrize(
    ("reviewer_error", "workbench_error"),
    (
        (
            ReviewerInvalidPullRequestURLError("invalid URL"),
            InvalidGitHubPullRequestError,
        ),
        (
            ReviewerGitHubRetrievalError("retrieval failed"),
            GitHubReviewRetrievalError,
        ),
        (
            ReviewerModelReviewError("model failed"),
            GitHubReviewExecutionError,
        ),
        (
            ReviewerReviewProtocolError("protocol failed"),
            GitHubReviewProtocolError,
        ),
        (
            PublicReviewerConfigurationError("configuration failed"),
            GitHubReviewConfigurationError,
        ),
        (
            PublicReviewerClosedError("reviewer closed"),
            GitHubReviewerClosedError,
        ),
    ),
)
def test_public_reviewer_errors_are_mapped_to_workbench_errors(
    reviewer_error: Exception,
    workbench_error: type[Exception],
) -> None:
    with pytest.raises(workbench_error, match=str(reviewer_error)) as error:
        GitHubReviewerAdapter(FakeRunner(reviewer_error)).review(URL)

    assert error.value.__cause__ is reviewer_error


def test_unknown_runner_exception_is_propagated_unchanged() -> None:
    expected = RuntimeError("unexpected failure")

    with pytest.raises(RuntimeError) as error:
        GitHubReviewerAdapter(FakeRunner(expected)).review(URL)

    assert error.value is expected


@pytest.mark.parametrize(
    ("severity", "assessment"),
    (("Unknown", "Approve"), ("Low", "Unknown")),
)
def test_invalid_external_result_fails_closed(
    severity: str,
    assessment: str,
) -> None:
    finding = FakeFinding(
        severity=severity,
        file_path="src/example.py",
        location="line 1",
        issue="Issue.",
        evidence="Evidence.",
        recommendation="Recommendation.",
    )

    with pytest.raises(GitHubReviewProtocolError, match="violates"):
        GitHubReviewerAdapter(
            FakeRunner(make_result(findings=(finding,), assessment=assessment))
        ).review(URL)


def test_owned_runner_close_is_idempotent_and_prevents_review() -> None:
    runner = FakeRunner(make_result())
    adapter = GitHubReviewerAdapter(runner, owns_runner=True)

    adapter.close()
    adapter.close()

    assert runner.close_calls == 1
    with pytest.raises(GitHubReviewerClosedError, match="closed"):
        adapter.review(URL)


def test_non_owned_runner_is_not_closed() -> None:
    runner = FakeRunner(make_result())
    adapter = GitHubReviewerAdapter(runner)

    adapter.close()

    assert runner.close_calls == 0


def test_adapter_uses_only_reviewer_root_api_and_has_no_github_write_path() -> None:
    source = Path(adapter_module.__file__).read_text(encoding="utf-8")
    public_methods = {
        name
        for name, member in inspect.getmembers(
            GitHubReviewerAdapter,
            predicate=inspect.isfunction,
        )
        if not name.startswith("_")
    }

    assert "from ai_github_reviewer import" in source
    assert "ai_github_reviewer." not in source
    assert "httpx" not in source
    assert public_methods == {"close", "review"}
    assert all(
        forbidden not in source
        for forbidden in (
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "github_token",
            "create_comment",
            "submit_review",
            "merge_pull_request",
        )
    )
