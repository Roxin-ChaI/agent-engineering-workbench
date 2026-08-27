class PromptExperimentError(RuntimeError):
    """Base error for the Workbench prompt experiment boundary."""


class InvalidPromptExperimentInputError(PromptExperimentError, ValueError):
    """Raised when a prompt experiment request cannot be executed."""


class PromptExperimentConfigurationError(PromptExperimentError):
    """Raised when the upstream prompt runner is not configured."""


class PromptExperimentModelError(PromptExperimentError):
    """Raised when the prompt experiment model request fails."""


class PromptExperimentEvaluationError(PromptExperimentError):
    """Raised when deterministic task evaluation fails."""


class PromptExperimentLifecycleError(PromptExperimentError):
    """Raised when the prompt experiment runner is unavailable."""


class PromptExperimentProtocolError(PromptExperimentError):
    """Raised when the upstream result violates the Workbench contract."""


class PromptExperimentExecutionError(PromptExperimentError):
    """Raised for an unexpected prompt experiment execution failure."""
