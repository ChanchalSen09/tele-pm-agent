"""Request Context Middleware for Correlation ID Injection."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.telemetry import set_correlation_id


class RequestContextMiddleware(BaseMiddleware):
    """Middleware that injects a unique correlation ID into request contexts."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Injects correlation_id into data dictionary and telemetry context variables."""
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)
        data["correlation_id"] = correlation_id
        return await handler(event, data)
