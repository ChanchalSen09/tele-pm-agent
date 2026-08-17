"""Unit tests for PII and Secret Sanitizer DLP Engine."""

from app.core.security_pii import sanitize_pii_and_secrets


def test_sanitize_pii_masks_emails() -> None:
    """Verifies email address masking."""
    text = "Contact john.doe@company.com for project updates."
    sanitized = sanitize_pii_and_secrets(text)
    assert "john.doe@company.com" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized


def test_sanitize_pii_masks_api_keys() -> None:
    """Verifies API key masking."""
    text = "Here is my key: AIzaSyD1234567890abcdefghijklmnopqrstuv"
    sanitized = sanitize_pii_and_secrets(text)
    assert "AIzaSyD1234567890abcdefghijklmnopqrstuv" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_pii_masks_jwt_tokens() -> None:
    """Verifies JWT token masking."""
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Authorization: Bearer {jwt}"
    sanitized = sanitize_pii_and_secrets(text)
    assert jwt not in sanitized
    assert "[REDACTED_JWT_TOKEN]" in sanitized
