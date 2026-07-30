"""Exception Handling Middleware for Telegram Ingress."""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.core.exceptions import BaseAppException

logger = structlog.get_logger(__name__)


class ExceptionHandlingMiddleware(BaseMiddleware):
    """Middleware catching exceptions and delivering user-friendly error replies."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Executes handler with exception safety net."""
        try:
            return await handler(event, data)
        except BaseAppException as app_exc:
            logger.warning(
                "Domain Exception caught in middleware",
                code=app_exc.code,
                message=app_exc.message,
            )
            await self._respond_error(event, f"⚠️ {app_exc.message}")
        except Exception as exc:
            logger.error(
                "Unhandled Exception caught in middleware",
                error=str(exc),
                exc_info=True,
            )
            correlation_id = data.get("correlation_id", "N/A")
            await self._respond_error(
                event,
                f"⚠️ An unexpected error occurred. Reference ID: `{correlation_id}`",
            )

    async def _respond_error(self, event: TelegramObject, error_text: str) -> None:
        """Utility delivering error response to user message if applicable."""
        if isinstance(event, Message):
            await event.answer(text=error_text, parse_mode="Markdown")
        else:
            msg = getattr(event, "message", None)
            if isinstance(msg, Message):
                await msg.answer(text=error_text, parse_mode="Markdown")
