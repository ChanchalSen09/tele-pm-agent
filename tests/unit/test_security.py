"""Unit tests for Security Utilities and Input Sanitization."""

from app.core.security import sanitize_input_text, validate_telegram_webhook_secret


def test_webhook_secret_validation() -> None:
    """Verifies HMAC constant-time secret validation."""
    assert (
        validate_telegram_webhook_secret("my_secret_token", "my_secret_token") is True
    )
    assert validate_telegram_webhook_secret("wrong_token", "my_secret_token") is False
    assert validate_telegram_webhook_secret("", "my_secret_token") is False


def test_input_sanitization() -> None:
    """Verifies control character stripping and length capping."""
    raw_input = "  Hello World\x00!  "
    clean = sanitize_input_text(raw_input)
    assert clean == "Hello World!"
    assert "\x00" not in clean

    long_input = "a" * 5000
    assert len(sanitize_input_text(long_input)) == 4000
