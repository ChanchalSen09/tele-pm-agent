"""Sliding-Window Rate Limiter & Quota Enforcement Module."""

import time
from collections import defaultdict
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    """Dataclass holding rate limit check result."""

    is_allowed: bool
    refusal_reason: str | None = None
    response_text: str | None = None


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter per Telegram chat_id."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, chat_id: int | None) -> RateLimitResult:
        """Evaluates whether chat_id has exceeded rate limit window."""
        if chat_id is None:
            return RateLimitResult(is_allowed=True)

        now = time.time()
        window_start = now - self.window_seconds

        # Filter out timestamps older than window_start
        timestamps = [ts for ts in self._history[chat_id] if ts > window_start]
        self._history[chat_id] = timestamps

        if len(timestamps) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for chat_id",
                chat_id=chat_id,
                requests=len(timestamps),
                limit=self.max_requests,
            )
            refusal_text = (
                "⚠️ *Rate Limit Exceeded*\n\n"
                "This group has sent too many requests in a short period. "
                "Please wait a moment before trying again!"
            )
            return RateLimitResult(
                is_allowed=False,
                refusal_reason="Rate limit exceeded",
                response_text=refusal_text,
            )

        self._history[chat_id].append(now)
        return RateLimitResult(is_allowed=True)

    def reset(self, chat_id: int) -> None:
        """Clears request history for target chat_id."""
        if chat_id in self._history:
            del self._history[chat_id]


# Singleton default rate limiter instance
default_rate_limiter = SlidingWindowRateLimiter()
