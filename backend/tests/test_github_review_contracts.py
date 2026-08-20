from dataclasses import FrozenInstanceError

import pytest
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
    GitHubReviewError,
    GitHubReviewExecutionError,
    GitHubReviewProtocolError,
    GitHubReviewRetrievalError,
    InvalidGitHubPullRequestError,
)


def make_result() -> GitHubReviewResult:
    return GitHubReviewResult(
        target=GitHubReviewTarget(
            owner="owner",
            repository="repository",
            pull_number=123,
        ),
        pull_request=GitHubPullRequestMetadata(
            title="Controlled change",
            state="open",
            author="reviewer",
            base_branch="main",
            head_branch="feature",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T00:00:00Z",
            changed_files=2,
            additions=4,
            deletions=1,
            commits=3,
        ),
        summary="Controlled summary.",
        findings=(
            GitHubReviewFinding(
                severity=GitHubReviewSeverity.HIGH,
                file_path="src/first.py",
                location="line 10",
                issue="First issue.",
                evidence="First evidence.",
                recommendation="First recommendation.",
            ),
            GitHubReviewFinding(
                severity=GitHubReviewSeverity.LOW,
                file_path="src/second.py",
                location="file-level",
                issue="Second issue.",
                evidence="Second evidence.",
                recommendation="Second recommendation.",
            ),
        ),
        test_gaps="Controlled test gap.",
        maintainability="Controlled maintainability note.",
        assessment=GitHubReviewAssessment.REQUEST_CHANGES,
        markdown="# Pull Request Review\n",
    )


def test_github_review_contract_preserves_public_result_fields() -> None:
    result = make_result()

    assert result.target == GitHubReviewTarget(
        owner="owner",
        repository="repository",
        pull_number=123,
    )
    assert result.pull_request.title == "Controlled change"
    assert result.summary == "Controlled summary."
    assert [finding.file_path for finding in result.findings] == [
        "src/first.py",
        "src/second.py",
    ]
    assert result.test_gaps == "Controlled test gap."
    assert result.maintainability == "Controlled maintainability note."
    assert result.assessment is GitHubReviewAssessment.REQUEST_CHANGES
    assert result.markdown == "# Pull Request Review\n"


def test_github_review_contract_is_immutable() -> None:
    result = make_result()

    with pytest.raises((FrozenInstanceError, ValidationError)):
        result.summary = "replacement"


def test_github_review_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        GitHubReviewTarget.model_validate(
            {
                "owner": "owner",
                "repository": "repository",
                "pull_number": 123,
                "confidence": 0.9,
            }
        )


@pytest.mark.parametrize("field_name", ("changed_files", "additions", "deletions", "commits"))
def test_pull_request_counts_must_not_be_negative(field_name: str) -> None:
    payload = make_result().pull_request.model_dump()
    payload[field_name] = -1

    with pytest.raises(ValidationError):
        GitHubPullRequestMetadata.model_validate(payload)


def test_review_severity_and_assessment_are_closed_contracts() -> None:
    finding_payload = make_result().findings[0].model_dump()
    finding_payload["severity"] = "Informational"

    with pytest.raises(ValidationError):
        GitHubReviewFinding.model_validate(finding_payload)
    with pytest.raises(ValidationError):
        GitHubReviewResult.model_validate(
            {**make_result().model_dump(), "assessment": "Unknown"}
        )


def test_domain_errors_share_one_workbench_boundary() -> None:
    error_types = (
        GitHubReviewConfigurationError,
        InvalidGitHubPullRequestError,
        GitHubReviewRetrievalError,
        GitHubReviewExecutionError,
        GitHubReviewProtocolError,
        GitHubReviewerClosedError,
    )

    assert all(issubclass(error_type, GitHubReviewError) for error_type in error_types)
