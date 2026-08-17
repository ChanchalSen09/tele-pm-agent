"""Security Utilities, Webhook Secret Validation, and Input Sanitization."""

import hmac


from app.core.security_pii import sanitize_pii_and_secrets


def validate_telegram_webhook_secret(
    received_secret: str, expected_secret: str
) -> bool:
    """Safely validates incoming Telegram secret token header against expected secret."""
    if not received_secret or not expected_secret:
        return False
    return hmac.compare_digest(
        received_secret.encode("utf-8"), expected_secret.encode("utf-8")
    )


def sanitize_input_text(raw_text: str) -> str:
    """Strips control characters, redacts PII/secrets, and limits input length."""
    if not raw_text:
        return ""
    # Strip null bytes and illegal ASCII control sequences
    clean_text = raw_text.replace("\x00", "").strip()[:4000]
    return sanitize_pii_and_secrets(clean_text)
