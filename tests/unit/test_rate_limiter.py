"""Unit tests for SlidingWindowRateLimiter."""

from app.core.rate_limiter import SlidingWindowRateLimiter


def test_sliding_window_rate_limiter_allows_under_limit() -> None:
    """Verifies requests within threshold are allowed."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    chat_id = -999

    assert limiter.is_allowed(chat_id).is_allowed is True
    assert limiter.is_allowed(chat_id).is_allowed is True
    assert limiter.is_allowed(chat_id).is_allowed is True


def test_sliding_window_rate_limiter_blocks_over_limit() -> None:
    """Verifies requests exceeding threshold trigger rate limit refusal."""
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    chat_id = -888

    assert limiter.is_allowed(chat_id).is_allowed is True
    assert limiter.is_allowed(chat_id).is_allowed is True

    res = limiter.is_allowed(chat_id)
    assert res.is_allowed is False
    assert res.refusal_reason == "Rate limit exceeded"
    assert "too many requests" in res.response_text
