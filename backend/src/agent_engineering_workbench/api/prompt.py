from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from agent_engineering_workbench.adapters.prompt_experiment import (
    PromptExperimentAdapter,
)
from agent_engineering_workbench.dependencies import (
    get_prompt_experiment_adapter,
    get_prompt_library_backend,
)
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
from agent_engineering_workbench.prompt_library_contracts import (
    PromptLibraryBackend,
    PromptLibraryCreateRequest,
    PromptLibraryItem,
    PromptLibraryList,
    PromptLibrarySearchRequest,
    PromptLibraryUpdateRequest,
)
from agent_engineering_workbench.prompt_library_errors import (
    InvalidPromptLibraryInputError,
    PromptLibraryInternalError,
    PromptLibraryNotFoundError,
    PromptLibraryUpstreamError,
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


@router.post(
    "/library",
    response_model=PromptLibraryItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_library_item(
    request: PromptLibraryCreateRequest,
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> PromptLibraryItem:
    try:
        return backend.create_prompt(request)
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)


@router.get("/library", response_model=PromptLibraryList)
async def list_prompt_library_items(
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> PromptLibraryList:
    try:
        return backend.list_prompts()
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)


@router.get("/library/search", response_model=PromptLibraryList)
async def search_prompt_library_items(
    q: Annotated[str, Query(min_length=1)],
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> PromptLibraryList:
    try:
        request = PromptLibrarySearchRequest(q=q)
        return backend.search_prompts(request)
    except ValidationError as exc:
        _raise_safe_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Prompt library input is invalid.",
            exc,
        )
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)


@router.get("/library/{prompt_id}", response_model=PromptLibraryItem)
async def get_prompt_library_item(
    prompt_id: int,
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> PromptLibraryItem:
    try:
        return backend.get_prompt(prompt_id)
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)


@router.put("/library/{prompt_id}", response_model=PromptLibraryItem)
async def update_prompt_library_item(
    prompt_id: int,
    request: PromptLibraryUpdateRequest,
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> PromptLibraryItem:
    try:
        return backend.update_prompt(prompt_id, request)
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)


@router.delete(
    "/library/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_prompt_library_item(
    prompt_id: int,
    backend: Annotated[
        PromptLibraryBackend,
        Depends(get_prompt_library_backend, scope="function"),
    ],
) -> Response:
    try:
        backend.delete_prompt(prompt_id)
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_prompt_library_http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _raise_prompt_library_http_error(error: Exception) -> NoReturn:
    if isinstance(error, InvalidPromptLibraryInputError):
        _raise_safe_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Prompt library input is invalid.",
            error,
        )
    if isinstance(error, PromptLibraryNotFoundError):
        _raise_safe_http_error(
            status.HTTP_404_NOT_FOUND,
            "Prompt library item was not found.",
            error,
        )
    if isinstance(error, PromptLibraryUpstreamError):
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Prompt library service is unavailable.",
            error,
        )
    if isinstance(error, PromptLibraryInternalError):
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Prompt library operation failed during internal processing.",
            error,
        )
    _raise_safe_http_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Prompt library operation failed during internal processing.",
        error,
    )


def _raise_safe_http_error(
    status_code: int,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail) from cause
