class ResumeOptimizationError(RuntimeError):
    """Base error for the Workbench resume optimization boundary."""


class ResumeOptimizationConfigurationError(ResumeOptimizationError, ValueError):
    """Raised when the resume optimizer production configuration is invalid."""


class InvalidResumeInputError(ResumeOptimizationError, ValueError):
    """Raised when resume optimization input cannot be accepted."""


class UnsupportedResumeFormatError(InvalidResumeInputError):
    """Raised when the resume document format is unsupported."""


class ResumeInputTooLargeError(InvalidResumeInputError):
    """Raised when resume optimization input exceeds a supported limit."""


class ResumeExtractionFailedError(InvalidResumeInputError):
    """Raised when usable text cannot be extracted from the resume."""


class ResumeOptimizationUpstreamError(ResumeOptimizationError):
    """Raised when the optimizer model request or response fails."""


class ResumeTruthfulnessError(ResumeOptimizationError):
    """Raised when the optimizer rejects an untruthful result."""


class ResumeOptimizationProtocolError(ResumeOptimizationError):
    """Raised when the optimizer violates its Workbench integration contract."""


class ResumeOptimizationInternalError(ResumeOptimizationError):
    """Raised for an unexpected failure inside the optimizer boundary."""


class ResumeOptimizerClosedError(ResumeOptimizationError):
    """Raised when a closed resume optimizer adapter is used."""


class ResumeOptimizationContractError(ResumeOptimizationProtocolError):
    """Raised by the result mapper when the public result contract drifts."""
