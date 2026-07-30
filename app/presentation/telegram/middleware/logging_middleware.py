"""Aiogram 3 Ingress Middleware for Request Tracing and Logging."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.core.telemetry import set_correlation_id

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware attaching correlation IDs and logging incoming Telegram updates."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)

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
                user_id = event.callback_query.from_user.id

        logger.info(
            "Telegram Update received",
            update_type=update_type,
            telegram_id=user_id,
            correlation_id=correlation_id,
        )

        try:
            return await handler(event, data)
        except Exception as exc:
            logger.error(
                "Unhandled error in Telegram Update handler",
                error=str(exc),
                correlation_id=correlation_id,
                exc_info=True,
            )
            raise
