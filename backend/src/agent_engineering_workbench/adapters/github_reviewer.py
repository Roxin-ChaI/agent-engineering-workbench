from collections.abc import Sequence
from typing import Protocol

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
from pydantic import ValidationError

from agent_engineering_workbench.github_review_contracts import (
    GitHubPullRequestMetadata,
    GitHubReviewAssessment,
    GitHubReviewFinding,
    GitHubReviewResult,
    GitHubReviewSeverity,
    GitHubReviewTarget,
)
from agent_engineering_workbench.github_review_errors import (
    GitHubReviewConfigurationError,
    GitHubReviewerClosedError,
    GitHubReviewExecutionError,
    GitHubReviewProtocolError,
    GitHubReviewRetrievalError,
    InvalidGitHubPullRequestError,
)


class ReviewerTargetLike(Protocol):
    @property
    def owner(self) -> str: ...

    @property
    def repository(self) -> str: ...

    @property
    def pull_number(self) -> int: ...


class ReviewerPullRequestLike(Protocol):
    @property
    def title(self) -> str: ...

    @property
    def state(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def base_branch(self) -> str: ...

    @property
    def head_branch(self) -> str: ...

    @property
    def created_at(self) -> str: ...

    @property
    def updated_at(self) -> str: ...

    @property
    def changed_files(self) -> int: ...

    @property
    def additions(self) -> int: ...

    @property
    def deletions(self) -> int: ...

    @property
    def commits(self) -> int: ...


class ReviewerFindingLike(Protocol):
    @property
    def severity(self) -> str: ...

    @property
    def file_path(self) -> str: ...

    @property
    def location(self) -> str: ...

    @property
    def issue(self) -> str: ...

    @property
    def evidence(self) -> str: ...

    @property
    def recommendation(self) -> str: ...


class ReviewerResultLike(Protocol):
    @property
    def target(self) -> ReviewerTargetLike: ...

    @property
    def pull_request(self) -> ReviewerPullRequestLike: ...

    @property
    def summary(self) -> str: ...

    @property
    def findings(self) -> Sequence[ReviewerFindingLike]: ...

    @property
    def test_gaps(self) -> str: ...

    @property
    def maintainability(self) -> str: ...

    @property
    def assessment(self) -> str: ...

    @property
    def markdown(self) -> str: ...


class GitHubReviewerRunner(Protocol):
    def review(self, pull_request_url: str) -> ReviewerResultLike: ...

    def close(self) -> None: ...


class GitHubReviewerAdapter:
    """Translate the Reviewer public result into Workbench-owned contracts."""

    def __init__(
        self,
        runner: GitHubReviewerRunner,
        *,
        owns_runner: bool = False,
    ) -> None:
        self._runner = runner
        self._owns_runner = owns_runner
        self._closed = False

    def review(self, pull_request_url: str) -> GitHubReviewResult:
        if self._closed:
            raise GitHubReviewerClosedError("GitHub reviewer adapter is closed")

        try:
            result = self._runner.review(pull_request_url)
        except ReviewerInvalidPullRequestURLError as exc:
            raise InvalidGitHubPullRequestError(str(exc)) from exc
        except ReviewerGitHubRetrievalError as exc:
            raise GitHubReviewRetrievalError(str(exc)) from exc
        except ReviewerModelReviewError as exc:
            raise GitHubReviewExecutionError(str(exc)) from exc
        except ReviewerReviewProtocolError as exc:
            raise GitHubReviewProtocolError(str(exc)) from exc
        except PublicReviewerConfigurationError as exc:
            raise GitHubReviewConfigurationError(str(exc)) from exc
        except PublicReviewerClosedError as exc:
            raise GitHubReviewerClosedError(str(exc)) from exc

        try:
            return self._map_result(result)
        except (ValidationError, ValueError) as exc:
            raise GitHubReviewProtocolError(
                "Reviewer result violates the Workbench GitHub review contract"
            ) from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_runner:
            self._runner.close()

    @staticmethod
    def _map_result(result: ReviewerResultLike) -> GitHubReviewResult:
        return GitHubReviewResult(
            target=GitHubReviewTarget(
                owner=result.target.owner,
                repository=result.target.repository,
                pull_number=result.target.pull_number,
            ),
            pull_request=GitHubPullRequestMetadata(
                title=result.pull_request.title,
                state=result.pull_request.state,
                author=result.pull_request.author,
                base_branch=result.pull_request.base_branch,
                head_branch=result.pull_request.head_branch,
                created_at=result.pull_request.created_at,
                updated_at=result.pull_request.updated_at,
                changed_files=result.pull_request.changed_files,
                additions=result.pull_request.additions,
                deletions=result.pull_request.deletions,
                commits=result.pull_request.commits,
            ),
            summary=result.summary,
            findings=tuple(
                GitHubReviewFinding(
                    severity=GitHubReviewSeverity(finding.severity),
                    file_path=finding.file_path,
                    location=finding.location,
                    issue=finding.issue,
                    evidence=finding.evidence,
                    recommendation=finding.recommendation,
                )
                for finding in result.findings
            ),
            test_gaps=result.test_gaps,
            maintainability=result.maintainability,
            assessment=GitHubReviewAssessment(result.assessment),
            markdown=result.markdown,
        )
