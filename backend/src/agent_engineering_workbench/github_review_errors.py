class GitHubReviewError(RuntimeError):
    """Base error for the Workbench GitHub review boundary."""


class GitHubReviewConfigurationError(GitHubReviewError, ValueError):
    """Raised when production GitHub review configuration is invalid."""


class InvalidGitHubPullRequestError(GitHubReviewError, ValueError):
    """Raised when the supplied GitHub Pull Request URL is invalid."""


class GitHubReviewRetrievalError(GitHubReviewError):
    """Raised when public Pull Request data cannot be retrieved."""


class GitHubReviewExecutionError(GitHubReviewError):
    """Raised when the review model cannot complete the review."""


class GitHubReviewProtocolError(GitHubReviewError):
    """Raised when the reviewer violates its public result protocol."""


class GitHubReviewerClosedError(GitHubReviewError):
    """Raised when a closed Workbench adapter is used."""
