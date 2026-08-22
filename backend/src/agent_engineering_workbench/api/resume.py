from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.requests import Request
from starlette.responses import JSONResponse

from agent_engineering_workbench.adapters.resume_optimizer import (
    ResumeOptimizerAdapter,
)
from agent_engineering_workbench.dependencies import get_resume_optimizer_adapter
from agent_engineering_workbench.resume_contracts import ResumeOptimizationResult
from agent_engineering_workbench.resume_errors import (
    InvalidResumeInputError,
    ResumeExtractionFailedError,
    ResumeInputTooLargeError,
    ResumeOptimizationConfigurationError,
    ResumeOptimizationInternalError,
    ResumeOptimizationProtocolError,
    ResumeOptimizationUpstreamError,
    ResumeOptimizerClosedError,
    ResumeTruthfulnessError,
    UnsupportedResumeFormatError,
)

MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARACTERS = 30_000
RESUME_UPLOAD_CHUNK_BYTES = 64 * 1024
SUPPORTED_RESUME_SUFFIXES = frozenset({".docx", ".pdf"})

router = APIRouter(prefix="/api/resume", tags=["resume"])


async def handle_resume_configuration_error(
    _request: Request,
    _error: Exception,
) -> JSONResponse:
    """Return a safe response for failures raised while resolving dependencies."""

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Resume optimizer is not configured."},
    )


@router.post("/optimize", response_model=ResumeOptimizationResult)
async def optimize_resume(
    resume: Annotated[UploadFile, File()],
    job_description: Annotated[str, Form()],
    adapter: Annotated[
        ResumeOptimizerAdapter,
        Depends(get_resume_optimizer_adapter),
    ],
) -> ResumeOptimizationResult:
    try:
        _validate_job_description(job_description)
        suffix = _validated_resume_suffix(resume.filename)
        with TemporaryDirectory(prefix="workbench-resume-") as temp_directory:
            resume_path = Path(temp_directory) / f"resume{suffix}"
            await _write_bounded_upload(resume, resume_path)
            return adapter.optimize(
                resume_path=resume_path,
                job_description=job_description,
            )
    except UnsupportedResumeFormatError as exc:
        _raise_safe_http_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Resume must be a PDF or DOCX file.",
            exc,
        )
    except ResumeInputTooLargeError as exc:
        _raise_safe_http_error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "Resume or job description exceeds the supported size limit.",
            exc,
        )
    except (InvalidResumeInputError, ResumeExtractionFailedError) as exc:
        _raise_safe_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Resume optimization input is invalid.",
            exc,
        )
    except (
        ResumeOptimizationUpstreamError,
        ResumeOptimizationProtocolError,
        ResumeTruthfulnessError,
    ) as exc:
        _raise_safe_http_error(
            status.HTTP_502_BAD_GATEWAY,
            "Resume optimizer returned an unusable result.",
            exc,
        )
    except ResumeOptimizationConfigurationError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Resume optimizer is not configured.",
            exc,
        )
    except ResumeOptimizerClosedError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Resume optimizer is unavailable.",
            exc,
        )
    except ResumeOptimizationInternalError as exc:
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Resume optimization failed during internal processing.",
            exc,
        )
    except Exception as exc:  # noqa: BLE001 - keep the HTTP boundary safe
        _raise_safe_http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Resume optimization failed during internal processing.",
            exc,
        )
    finally:
        await resume.close()


def _validate_job_description(job_description: str) -> None:
    if not job_description.strip():
        raise InvalidResumeInputError("Job description must not be empty.")
    if len(job_description) > MAX_JOB_DESCRIPTION_CHARACTERS:
        raise ResumeInputTooLargeError("Job description is too large.")


def _validated_resume_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_RESUME_SUFFIXES:
        raise UnsupportedResumeFormatError("Unsupported resume format.")
    return suffix


async def _write_bounded_upload(upload: UploadFile, destination: Path) -> None:
    total_bytes = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(RESUME_UPLOAD_CHUNK_BYTES):
            total_bytes += len(chunk)
            if total_bytes > MAX_RESUME_UPLOAD_BYTES:
                raise ResumeInputTooLargeError("Resume upload is too large.")
            output.write(chunk)

    if total_bytes == 0:
        raise InvalidResumeInputError("Resume upload must not be empty.")


def _raise_safe_http_error(
    status_code: int,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail) from cause
