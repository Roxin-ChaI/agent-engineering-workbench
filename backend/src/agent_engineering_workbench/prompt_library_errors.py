class PromptLibraryError(RuntimeError):
    """Base error for the Workbench prompt library boundary."""


class InvalidPromptLibraryInputError(PromptLibraryError, ValueError):
    """Raised when a prompt library request is invalid."""


class PromptLibraryNotFoundError(PromptLibraryError):
    """Raised when a requested prompt library item does not exist."""


class PromptLibraryUpstreamError(PromptLibraryError):
    """Raised when Prompt Vault is unavailable or returns an error."""


class PromptLibraryInternalError(PromptLibraryError):
    """Raised for an unexpected Workbench prompt library failure."""
