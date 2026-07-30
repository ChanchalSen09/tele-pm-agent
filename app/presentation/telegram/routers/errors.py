"""Global Errors Router for Aiogram Dispatcher."""

import structlog
from aiogram import Router
from aiogram.types import ErrorEvent

router = Router(name="errors_router")
logger = structlog.get_logger(__name__)


@router.errors()
async def global_error_handler(event: ErrorEvent) -> None:
    """Global Aiogram Error Handler catching uncaught update exceptions.

    Logs error with exception trace and responds gracefully if event message exists.
    """
    logger.error(
        "Global Aiogram Error caught",
        error=str(event.exception),
        exc_info=event.exception,
    )
    if event.update.message:
        await event.update.message.answer(
            text="⚠️ An unexpected error occurred while processing your message.",
            parse_mode="Markdown",
        )
