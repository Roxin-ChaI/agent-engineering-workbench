from pathlib import Path
from typing import Protocol

from ai_resume_optimizer import (  # type: ignore[import-untyped]
    ConfigurationError as PublicConfigurationError,
)
from ai_resume_optimizer import (
    InputError as PublicInputError,
)
from ai_resume_optimizer import (
    InputTooLargeError as PublicInputTooLargeError,
)
from ai_resume_optimizer import (
    ModelCallError as PublicModelCallError,
)
from ai_resume_optimizer import (
    ModelOutputError as PublicModelOutputError,
)
from ai_resume_optimizer import (
    OptimizationResult,
)
from ai_resume_optimizer import (
    OutputError as PublicOutputError,
)
from ai_resume_optimizer import (
    ResumeExtractionError as PublicResumeExtractionError,
)
from ai_resume_optimizer import (
    ResumeOptimizerClosedError as PublicResumeOptimizerClosedError,
)
from ai_resume_optimizer import (
    ResumeOptimizerError as PublicResumeOptimizerError,
)
from ai_resume_optimizer import (
    TruthfulnessError as PublicTruthfulnessError,
)
from ai_resume_optimizer import (
    UnsupportedFormatError as PublicUnsupportedFormatError,
)

from agent_engineering_workbench.resume_contracts import ResumeOptimizationResult
from agent_engineering_workbench.resume_errors import (
    InvalidResumeInputError,
    ResumeExtractionFailedError,
    ResumeInputTooLargeError,
    ResumeOptimizationConfigurationError,
    ResumeOptimizationContractError,
    ResumeOptimizationInternalError,
    ResumeOptimizationProtocolError,
    ResumeOptimizationUpstreamError,
    ResumeOptimizerClosedError,
    ResumeTruthfulnessError,
    UnsupportedResumeFormatError,
)
from agent_engineering_workbench.resume_mapping import (
    map_resume_optimization_result,
)


class ResumeOptimizerRunnerProtocol(Protocol):
    """Minimal public runner behavior required by the Workbench adapter."""

    def optimize(
        self,
        *,
        resume_path: Path,
        job_description: str,
    ) -> OptimizationResult: ...

    def close(self) -> None: ...


class ResumeOptimizerAdapter:
    """Translate Resume Optimizer results and errors into Workbench contracts."""

    def __init__(self, runner: ResumeOptimizerRunnerProtocol) -> None:
        self._runner = runner
        self._closed = False

    def optimize(
        self,
        *,
        resume_path: Path,
        job_description: str,
    ) -> ResumeOptimizationResult:
        if self._closed:
            raise ResumeOptimizerClosedError("Resume optimizer is unavailable.")

        try:
            result = self._runner.optimize(
                resume_path=resume_path,
                job_description=job_description,
            )
        except PublicUnsupportedFormatError as exc:
            raise UnsupportedResumeFormatError(
                "Resume must be a PDF or DOCX file."
            ) from exc
        except PublicInputTooLargeError as exc:
            raise ResumeInputTooLargeError(
                "Resume or job description exceeds the supported size limit."
            ) from exc
        except PublicInputError as exc:
            raise InvalidResumeInputError(
                "Resume optimization input is invalid."
            ) from exc
        except PublicResumeExtractionError as exc:
            raise ResumeExtractionFailedError(
                "Unable to extract usable text from the resume."
            ) from exc
        except PublicModelCallError as exc:
            raise ResumeOptimizationUpstreamError(
                "Resume optimizer model request failed."
            ) from exc
        except PublicModelOutputError as exc:
            raise ResumeOptimizationProtocolError(
                "Resume optimizer returned an invalid model result."
            ) from exc
        except PublicTruthfulnessError as exc:
            raise ResumeTruthfulnessError(
                "Resume optimization failed truthfulness validation."
            ) from exc
        except PublicConfigurationError as exc:
            raise ResumeOptimizationConfigurationError(
                "Resume optimizer is not configured."
            ) from exc
        except PublicResumeOptimizerClosedError as exc:
            raise ResumeOptimizerClosedError(
                "Resume optimizer is unavailable."
            ) from exc
        except PublicOutputError as exc:
            raise ResumeOptimizationInternalError(
                "Resume optimizer failed during internal processing."
            ) from exc
        except PublicResumeOptimizerError as exc:
            raise ResumeOptimizationInternalError(
                "Resume optimizer failed during internal processing."
            ) from exc
        except Exception as exc:
            raise ResumeOptimizationInternalError(
                "Resume optimizer failed during internal processing."
            ) from exc

        try:
            return map_resume_optimization_result(result)
        except ResumeOptimizationContractError as exc:
            raise ResumeOptimizationProtocolError(
                "Resume optimizer returned an incompatible result."
            ) from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._runner.close()
