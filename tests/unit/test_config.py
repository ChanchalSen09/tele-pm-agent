"""Unit tests for Application Settings and Exception Hierarchy."""

from app.core.config import AppEnvironment, settings
from app.core.exceptions import DomainException, RateLimitExceededException


def test_settings_load() -> None:
    """Verifies settings load default environment values correctly."""
    assert settings.APP_ENV in [
        AppEnvironment.DEVELOPMENT,
        AppEnvironment.PRODUCTION,
        AppEnvironment.TESTING,
        AppEnvironment.STAGING,
    ]
    assert isinstance(settings.GEMINI_MODEL_NAME, str)
    assert len(settings.GEMINI_MODEL_NAME) > 0


def test_exception_hierarchy() -> None:
    """Verifies domain and infrastructure exception inheritance and attributes."""
    exc = RateLimitExceededException(retry_after=45)
    assert exc.status_code == 400
    assert exc.code == "ERR_RATE_LIMIT_EXCEEDED"
    assert exc.details["retry_after"] == 45
    assert isinstance(exc, DomainException)
