"""Aiogram Dispatcher Factory, Middleware Pipeline, and Event Callbacks."""

import structlog
from aiogram import Bot, Dispatcher

from app.presentation.telegram.middleware.context import RequestContextMiddleware
from app.presentation.telegram.middleware.errors import ExceptionHandlingMiddleware
from app.presentation.telegram.middleware.logging import LoggingMiddleware
from app.presentation.telegram.routers import chat, errors, health, standup, start

logger = structlog.get_logger(__name__)


async def on_startup(bot: Bot) -> None:
    """Startup lifecycle callback executed when dispatcher initializes."""
    bot_info = await bot.get_me()
    logger.info(
        "Telegram Bot initialized and starting",
        bot_id=bot_info.id,
        bot_username=bot_info.username,
    )


async def on_shutdown(bot: Bot) -> None:
    """Shutdown lifecycle callback executed when dispatcher terminates."""
    logger.info("Telegram Bot shutting down...")


def setup_dispatcher() -> Dispatcher:
    """Factory creating and configuring the Aiogram Dispatcher with middlewares and routers."""
    dp = Dispatcher()

    # Register Lifecycle Callbacks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Register Global Middlewares (in execution order)
    dp.update.outer_middleware(RequestContextMiddleware())
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.middleware(ExceptionHandlingMiddleware())

    # Register Routers safely handling module reloads
    for r in (start.router, health.router, standup.router, chat.router, errors.router):
        r._parent_router = None
        dp.include_router(r)

    return dp
