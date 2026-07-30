"""Logging Middleware for Update Ingestion and Duration Tracking."""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware logging incoming update metadata and processing duration."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Logs start and completion of Telegram update processing."""
        start_time = time.perf_counter()
        correlation_id = data.get("correlation_id", "unknown")
        update_type = "unknown"
        user_id = None

        if isinstance(event, Update):
            if event.message:
                update_type = "message"
                user_id = (
                    event.message.from_user.id if event.message.from_user else None
                )
            elif event.callback_query:
                update_type = "callback_query"
                user_id = (
                    event.callback_query.from_user.id
                    if event.callback_query.from_user
                    else None
                )

        logger.info(
            "Telegram Update Processing Started",
            update_type=update_type,
            user_id=user_id,
            correlation_id=correlation_id,
        )

        try:
            result = await handler(event, data)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Telegram Update Processing Completed",
                update_type=update_type,
                user_id=user_id,
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Telegram Update Processing Failed",
                update_type=update_type,
                user_id=user_id,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                correlation_id=correlation_id,
                exc_info=True,
            )
            raise
