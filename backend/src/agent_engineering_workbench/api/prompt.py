from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from starlette.responses import JSONResponse

from agent_engineering_workbench.adapters.prompt_experiment import (
    PromptExperimentAdapter,
)
from agent_engineering_workbench.dependencies import get_prompt_experiment_adapter
from agent_engineering_workbench.prompt_contracts import (
    PromptExperimentRequest,
    PromptExperimentResult,
)
from agent_engineering_workbench.prompt_errors import (
    InvalidPromptExperimentInputError,
    PromptExperimentConfigurationError,
    PromptExperimentEvaluationError,
    PromptExperimentExecutionError,
    PromptExperimentLifecycleError,
    PromptExperimentModelError,
    PromptExperimentProtocolError,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


async def handle_prompt_configuration_error(
    _request: Request,
    _error: Exception,
) -> JSONResponse:
    """Return a safe response when dependency configuration fails."""

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Prompt experiment service is not configured."},
    )


async def handle_prompt_lifecycle_error(
    _request: Request,
    _error: Exception,
) -> JSONResponse:
    """Return a safe response when request-scoped cleanup fails."""

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Prompt experiment service is unavailable."},
    )


async def handle_prompt_model_error(
    _request: Request,
    _error: Exception,
) -> JSONResponse:
    """Return a safe response when model setup fails during dependency resolution."""

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": "Prompt experiment model request failed."},
    )


@router.post("/experiment", response_model=PromptExperimentResult)
async def run_prompt_experiment(
    request: PromptExperimentRequest,
    adapter: Annotated[
        PromptExperimentAdapter,
        Depends(get_prompt_experiment_adapter, scope="function"),
    ],
) -> PromptExperimentResult:
    try:
        return adapter.run(request)
    except InvalidPromptExperimentInputError as exc:
        _raise_safe_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Prompt experiment input is invalid.",
            exc,
        )
    except PromptExperimentModelError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Prompt experiment model request failed.",
            exc,
        )
    except PromptExperimentEvaluationError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Prompt experiment evaluation failed.",
            exc,
        )
    except PromptExperimentProtocolError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Prompt experiment returned an invalid result.",
            exc,
        )
    except PromptExperimentExecutionError as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Prompt experiment execution failed.",
            exc,
        )
    except PromptExperimentConfigurationError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Prompt experiment service is not configured.",
            exc,
        )
    except PromptExperimentLifecycleError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Prompt experiment service is unavailable.",
            exc,
        )
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Prompt experiment failed during internal processing.",
            exc,
        )


def _raise_safe_http_error(
    status_code: int,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail) from cause
