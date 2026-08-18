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
            user_msg = self._format_human_error(app_exc.message, app_exc.code)
            await self._respond_error(event, user_msg)
        except Exception as exc:
            logger.error(
                "Unhandled Exception caught in middleware",
                error=str(exc),
                exc_info=True,
            )
            correlation_id = data.get("correlation_id", "N/A")
            await self._respond_error(
                event,
                "🤖 *I ran into a temporary hiccup while processing your message.*\n\nPlease try again in a few seconds!",
            )

    def _format_human_error(self, message: str, code: str) -> str:
        """Transforms raw technical exceptions into natural, human-friendly responses."""
        msg_lower = message.lower()

        # Check for AI Service High Demand / 503 / Rate limit / LLM failures
        if (
            code in ("ERR_LLM_FAILURE", "ERR_RATE_LIMIT_EXCEEDED")
            or "503" in msg_lower
            or "unavailable" in msg_lower
            or "high demand" in msg_lower
            or "quota" in msg_lower
            or "resource_exhausted" in msg_lower
        ):
            return (
                "🤖 *I'm experiencing a brief AI service overload right now.*\n\n"
                "Please try sending your message again in a few seconds! 🙏"
            )

        # Check if message contains raw JSON, dicts, or SQL technical dumps
        if "{" in message or "code':" in msg_lower or "[sql:" in msg_lower or "traceback" in msg_lower:
            return (
                "🤖 *I ran into a temporary issue while processing your request.*\n\n"
                "Please try again shortly!"
            )

        # Clean business logic validation messages
        clean_msg = message.replace("Gemini API failure:", "").strip()
        return f"⚠️ {clean_msg}"

    async def _respond_error(self, event: TelegramObject, error_text: str) -> None:
        """Utility delivering error response to user message if applicable."""
        if isinstance(event, Message):
            await event.answer(text=error_text, parse_mode="Markdown")
        else:
            msg = getattr(event, "message", None)
            if isinstance(msg, Message):
                await msg.answer(text=error_text, parse_mode="Markdown")
