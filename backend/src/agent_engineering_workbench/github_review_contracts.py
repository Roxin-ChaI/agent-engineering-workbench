from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _ImmutableGitHubReviewContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GitHubReviewSeverity(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class GitHubReviewAssessment(StrEnum):
    APPROVE = "Approve"
    APPROVE_WITH_MINOR_COMMENTS = "Approve with minor comments"
    REQUEST_CHANGES = "Request changes"
    INSUFFICIENT_DATA = "Insufficient data"


class GitHubReviewTarget(_ImmutableGitHubReviewContract):
    owner: str
    repository: str
    pull_number: int = Field(gt=0)


class GitHubPullRequestMetadata(_ImmutableGitHubReviewContract):
    title: str
    state: str
    author: str
    base_branch: str
    head_branch: str
    created_at: str
    updated_at: str
    changed_files: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    commits: int = Field(ge=0)


class GitHubReviewFinding(_ImmutableGitHubReviewContract):
    severity: GitHubReviewSeverity
    file_path: str
    location: str
    issue: str
    evidence: str
    recommendation: str


class GitHubReviewResult(_ImmutableGitHubReviewContract):
    target: GitHubReviewTarget
    pull_request: GitHubPullRequestMetadata
    summary: str
    findings: tuple[GitHubReviewFinding, ...]
    test_gaps: str
    maintainability: str
    assessment: GitHubReviewAssessment
    markdown: str
