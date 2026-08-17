"""PII & Secret Sanitizer Engine for Enterprise Data Loss Prevention (DLP)."""

import re

import structlog

logger = structlog.get_logger(__name__)

# Patterns for masking sensitive organizational credentials and PII
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_API_KEY_PATTERN = re.compile(
    r"\b(sk-[a-zA-Z0-9]{32,}|AIzaSy[a-zA-Z0-9_-]{33}|ghp_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9_-]{20})\b"
)
_JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b")
_CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def sanitize_pii_and_secrets(text: str) -> str:
    """Scrubs PII, API tokens, JWTs, and credit card numbers from user prompt payloads.

    Replaces sensitive data with safe placeholders before sending prompts to external APIs.
    """
    if not text:
        return ""

    sanitized = text

    # Mask API Keys
    if _API_KEY_PATTERN.search(sanitized):
        sanitized = _API_KEY_PATTERN.sub("[REDACTED_API_KEY]", sanitized)
        logger.info("DLP Engine Masked API Key in prompt payload")

    # Mask JWT Tokens
    if _JWT_PATTERN.search(sanitized):
        sanitized = _JWT_PATTERN.sub("[REDACTED_JWT_TOKEN]", sanitized)
        logger.info("DLP Engine Masked JWT Token in prompt payload")

    # Mask Credit Card Numbers
    if _CREDIT_CARD_PATTERN.search(sanitized):
        sanitized = _CREDIT_CARD_PATTERN.sub("[REDACTED_CARD_NUMBER]", sanitized)
        logger.info("DLP Engine Masked Credit Card in prompt payload")

    # Mask Email Addresses
    if _EMAIL_PATTERN.search(sanitized):
        sanitized = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)

    return sanitized
