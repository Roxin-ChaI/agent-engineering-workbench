import inspect
import logging
from collections.abc import Iterator

import pytest
from ai_github_reviewer import (  # type: ignore[import-untyped]
    ModelReviewError as ReviewerModelReviewError,
)
from fastapi.testclient import TestClient

import agent_engineering_workbench.api.github as github_api
from agent_engineering_workbench.app import app
from agent_engineering_workbench.dependencies import get_github_review_adapter
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

PR_URL = "https://github.com/owner/repository/pull/123"


class FakeGitHubReviewerAdapter:
    def __init__(self, outcome: GitHubReviewResult | BaseException) -> None:
        self.outcome = outcome
        self.urls: list[str] = []

    def review(self, pull_request_url: str) -> GitHubReviewResult:
        self.urls.append(pull_request_url)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Iterator[None]:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def review_result(
    *,
    findings: tuple[GitHubReviewFinding, ...] = (
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
) -> GitHubReviewResult:
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
        findings=findings,
        test_gaps="Controlled test gap.",
        maintainability="Controlled maintainability note.",
        assessment=GitHubReviewAssessment.REQUEST_CHANGES,
        markdown="# Pull Request Review\n",
    )


def install_fake_adapter(adapter: FakeGitHubReviewerAdapter) -> None:
    app.dependency_overrides[get_github_review_adapter] = lambda: adapter


def execution_error_with_root(root_error: Exception) -> GitHubReviewExecutionError:
    try:
        try:
            raise root_error
        except Exception as exc:
            raise ReviewerModelReviewError("hidden reviewer model failure") from exc
    except ReviewerModelReviewError as exc:
        try:
            raise GitHubReviewExecutionError("hidden Workbench failure") from exc
        except GitHubReviewExecutionError as error:
            return error


def test_github_review_returns_complete_workbench_contract() -> None:
    adapter = FakeGitHubReviewerAdapter(review_result())
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": PR_URL},
    )

    assert response.status_code == 200
    assert adapter.urls == [PR_URL]
    assert response.json() == {
        "target": {
            "owner": "owner",
            "repository": "repository",
            "pull_number": 123,
        },
        "pull_request": {
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
        },
        "summary": "Controlled summary.",
        "findings": [
            {
                "severity": "High",
                "file_path": "src/first.py",
                "location": "line 10",
                "issue": "First issue.",
                "evidence": "First evidence.",
                "recommendation": "First recommendation.",
            },
            {
                "severity": "Low",
                "file_path": "src/second.py",
                "location": "file-level",
                "issue": "Second issue.",
                "evidence": "Second evidence.",
                "recommendation": "Second recommendation.",
            },
        ],
        "test_gaps": "Controlled test gap.",
        "maintainability": "Controlled maintainability note.",
        "assessment": "Request changes",
        "markdown": "# Pull Request Review\n",
    }


def test_empty_findings_are_serialized_as_an_empty_collection() -> None:
    adapter = FakeGitHubReviewerAdapter(review_result(findings=()))
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": PR_URL},
    )

    assert response.status_code == 200
    assert response.json()["findings"] == []
    assert adapter.urls == [PR_URL]


def test_pr_url_is_normalized_and_adapter_is_called_once() -> None:
    adapter = FakeGitHubReviewerAdapter(review_result())
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": f"  {PR_URL}  "},
    )

    assert response.status_code == 200
    assert adapter.urls == [PR_URL]


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"pr_url": ""},
        {"pr_url": "   "},
        {"pr_url": PR_URL, "github_token": "forbidden"},
    ),
)
def test_invalid_request_returns_standard_422(
    payload: dict[str, object],
) -> None:
    adapter = FakeGitHubReviewerAdapter(review_result())
    install_fake_adapter(adapter)

    response = TestClient(app).post("/api/github/review", json=payload)

    assert response.status_code == 422
    assert adapter.urls == []


def test_malformed_json_returns_standard_422() -> None:
    adapter = FakeGitHubReviewerAdapter(review_result())
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        content=b'{"pr_url":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"
    assert adapter.urls == []


def test_invalid_pull_request_url_returns_semantic_validation_response() -> None:
    adapter = FakeGitHubReviewerAdapter(
        InvalidGitHubPullRequestError("invalid public Pull Request URL")
    )
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": "not-a-pull-request"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "invalid public Pull Request URL"
    }
    assert adapter.urls == ["not-a-pull-request"]


@pytest.mark.parametrize(
    ("adapter_error", "expected_detail", "expected_category"),
    (
        (
            GitHubReviewRetrievalError("secret retrieval failure"),
            "Unable to retrieve the public pull request.",
            "retrieval",
        ),
        (
            GitHubReviewExecutionError("secret model failure"),
            "Unable to generate the pull request review.",
            "execution",
        ),
        (
            GitHubReviewProtocolError("secret protocol failure"),
            "Reviewer returned an invalid review result.",
            "protocol",
        ),
    ),
)
def test_upstream_errors_return_safe_502(
    adapter_error: Exception,
    expected_detail: str,
    expected_category: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = FakeGitHubReviewerAdapter(adapter_error)
    install_fake_adapter(adapter)

    with caplog.at_level(logging.WARNING, logger=github_api.__name__):
        response = TestClient(app).post(
            "/api/github/review",
            json={"pr_url": PR_URL},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert f"github_review_failure category={expected_category}" in caplog.text
    assert "secret" not in caplog.text
    assert adapter.urls == [PR_URL]


def test_execution_failure_logs_only_safe_root_exception_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class OriginalError(Exception):
        pass

    adapter = FakeGitHubReviewerAdapter(
        execution_error_with_root(OriginalError("private provider message"))
    )
    install_fake_adapter(adapter)

    with caplog.at_level(logging.WARNING, logger=github_api.__name__):
        response = TestClient(app).post(
            "/api/github/review",
            json={"pr_url": PR_URL},
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Unable to generate the pull request review."
    }
    assert "github_review_failure category=execution" in caplog.text
    assert "root_exception_type=OriginalError" in caplog.text
    assert "upstream_status=none" in caplog.text
    assert "private provider message" not in caplog.text


def test_execution_failure_logs_safe_integer_status_without_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FakeProviderError(Exception):
        status_code = 400

    secret_values = (
        "sk-secret-test",
        "https://api.deepseek.com/sensitive",
        "Authorization: Bearer secret",
        "provider raw body",
    )
    adapter = FakeGitHubReviewerAdapter(
        execution_error_with_root(FakeProviderError(" ".join(secret_values)))
    )
    install_fake_adapter(adapter)

    with caplog.at_level(logging.WARNING, logger=github_api.__name__):
        response = TestClient(app).post(
            "/api/github/review",
            json={"pr_url": PR_URL},
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Unable to generate the pull request review."
    }
    assert "root_exception_type=FakeProviderError" in caplog.text
    assert "upstream_status=400" in caplog.text
    for secret in secret_values:
        assert secret not in caplog.text
        assert secret not in response.text
    assert "FakeProviderError" not in response.text
    assert "400" not in response.text


def test_root_cause_traversal_stops_on_a_cycle() -> None:
    first = RuntimeError("first")
    second = ValueError("second")
    first.__cause__ = second
    second.__cause__ = first

    assert github_api._root_cause(first) is second


@pytest.mark.parametrize(
    ("adapter_error", "expected_detail"),
    (
        (
            GitHubReviewConfigurationError("secret configuration failure"),
            "GitHub reviewer is not configured.",
        ),
        (
            GitHubReviewerClosedError("secret closed failure"),
            "GitHub reviewer is unavailable.",
        ),
    ),
)
def test_known_internal_errors_return_safe_500(
    adapter_error: Exception,
    expected_detail: str,
) -> None:
    adapter = FakeGitHubReviewerAdapter(adapter_error)
    install_fake_adapter(adapter)

    response = TestClient(app).post(
        "/api/github/review",
        json={"pr_url": PR_URL},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert adapter.urls == [PR_URL]


def test_unknown_adapter_exception_is_not_converted_to_success() -> None:
    expected = RuntimeError("unexpected internal failure")
    adapter = FakeGitHubReviewerAdapter(expected)
    install_fake_adapter(adapter)

    with pytest.raises(RuntimeError) as error:
        TestClient(app).post(
            "/api/github/review",
            json={"pr_url": PR_URL},
        )

    assert error.value is expected
    assert adapter.urls == [PR_URL]


def test_route_is_registered_without_changing_existing_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/api/github/review" in paths
    assert "/api/context/compress" in paths
    assert "/api/research/web" in paths
    assert "/api/research/knowledge" in paths
    assert "/health" in paths


def test_github_review_api_has_no_token_or_github_write_path() -> None:
    source = inspect.getsource(github_api)

    assert all(
        forbidden not in source
        for forbidden in (
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "github_token",
            "create_comment",
            "submit_review",
            "approve_pull_request",
            "request_changes",
            "merge_pull_request",
            "httpx",
            "requests",
        )
    )
