"""Domain error hierarchy for the Dance Coaching Platform.

All domain-specific exceptions inherit from DomainError to allow
consistent error handling across application and infrastructure layers.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors.

    Attributes:
        code: A machine-readable error code for programmatic handling.
        message: A human-readable description of the error.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class ValidationError(DomainError):
    """Raised when input data fails domain validation rules.

    Examples: invalid file paths, out-of-range values, malformed data.
    """

    def __init__(self, message: str) -> None:
        super().__init__(code="VALIDATION_ERROR", message=message)


class BackendError(DomainError):
    """Raised when a generation backend encounters an error.

    Examples: API failures, model errors, timeout issues.
    """

    def __init__(self, message: str) -> None:
        super().__init__(code="BACKEND_ERROR", message=message)


class PipelineError(DomainError):
    """Raised when the processing pipeline encounters an error.

    Examples: FFmpeg failures, audio extraction errors, segment processing issues.
    """

    def __init__(self, message: str) -> None:
        super().__init__(code="PIPELINE_ERROR", message=message)


class InsufficientResourceError(BackendError):
    """Raised when system resources are insufficient for the operation.

    Examples: GPU out-of-memory, disk space exhaustion, memory limits.
    """

    def __init__(self, message: str) -> None:
        # Override BackendError.__init__ to set a more specific code
        DomainError.__init__(
            self,
            code="INSUFFICIENT_RESOURCE",
            message=message,
        )
