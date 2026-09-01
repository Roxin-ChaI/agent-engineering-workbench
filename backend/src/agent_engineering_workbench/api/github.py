import logging
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator

from agent_engineering_workbench.adapters.github_reviewer import (
    GitHubReviewerAdapter,
)
from agent_engineering_workbench.dependencies import get_github_review_adapter
from agent_engineering_workbench.github_review_contracts import (
    GitHubReviewResult,
)
from agent_engineering_workbench.github_review_errors import (
    GitHubReviewConfigurationError,
    GitHubReviewerClosedError,
    GitHubReviewExecutionError,
    GitHubReviewProtocolError,
    GitHubReviewRetrievalError,
    InvalidGitHubPullRequestError,
)

logger = logging.getLogger(__name__)


class GitHubReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pr_url: str

    @field_validator("pr_url")
    @classmethod
    def validate_pr_url(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("pr_url must not be empty")
        return normalized_value


router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/review", response_model=GitHubReviewResult)
async def review_pull_request(
    request: GitHubReviewRequest,
    adapter: Annotated[
        GitHubReviewerAdapter,
        Depends(get_github_review_adapter),
    ],
) -> GitHubReviewResult:
    try:
        return adapter.review(request.pr_url)
    except InvalidGitHubPullRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except GitHubReviewRetrievalError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Unable to retrieve the public pull request.",
            exc,
            category="retrieval",
        )
    except GitHubReviewExecutionError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Unable to generate the pull request review.",
            exc,
            category="execution",
        )
    except GitHubReviewProtocolError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Reviewer returned an invalid review result.",
            exc,
            category="protocol",
        )
    except GitHubReviewConfigurationError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "GitHub reviewer is not configured.",
            exc,
            category="configuration",
        )
    except GitHubReviewerClosedError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "GitHub reviewer is unavailable.",
            exc,
            category="closed",
        )


def _raise_safe_http_error(
    status_code: int,
    detail: str,
    cause: Exception,
    *,
    category: str,
) -> NoReturn:
    root_cause = _root_cause(cause)
    upstream_status = getattr(root_cause, "status_code", None)
    if type(upstream_status) is not int:
        upstream_status = None
    logger.warning(
        "github_review_failure category=%s root_exception_type=%s upstream_status=%s",
        category,
        type(root_cause).__name__,
        upstream_status if upstream_status is not None else "none",
    )
    raise HTTPException(status_code=status_code, detail=detail) from cause


def _root_cause(error: BaseException) -> BaseException:
    current = error
    seen: set[int] = set()
    while current.__cause__ is not None and id(current.__cause__) not in seen:
        seen.add(id(current))
        current = current.__cause__
    return current
