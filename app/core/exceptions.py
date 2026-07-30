"""Global Application Exception Hierarchy."""

from typing import Any


class BaseAppException(Exception):
    """Base class for all domain and infrastructure exceptions."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "ERR_INTERNAL",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DomainException(BaseAppException):
    """Exception raised when a business domain rule is violated."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_DOMAIN_VIOLATION",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=400, details=details)


class RateLimitExceededException(DomainException):
    """Exception raised when a user exceeds their rate limit quota."""

    def __init__(self, retry_after: int = 60) -> None:
        super().__init__(
            message=f"Rate limit exceeded. Please retry in {retry_after} seconds.",
            code="ERR_RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after},
        )


class InfrastructureException(BaseAppException):
    """Exception raised during third-party or technical infrastructure failure."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_INFRASTRUCTURE_FAILURE",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=502, details=details)


class LLMException(InfrastructureException):
    """Exception raised during Google Gemini API execution errors."""

    def __init__(
        self,
        message: str = "AI Generation service error",
        code: str = "ERR_LLM_FAILURE",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, details=details)


class DatabaseException(InfrastructureException):
    """Exception raised during database connectivity or transactional errors."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code="ERR_DATABASE_FAILURE", details=details)


class ValidationException(BaseAppException):
    """Exception raised when input payload validation fails."""

    def __init__(
        self,
        message: str = "Input validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="ERR_VALIDATION_FAILED",
            status_code=422,
            details=details,
        )
