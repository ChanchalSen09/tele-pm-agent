"""Dedicated Single-Process Telegram Bot Long Polling Runner."""

import asyncio
import structlog

from app.core.config import settings
from app.core.logger_setup import setup_logging
from app.presentation.telegram.bot import create_bot_and_dispatcher

setup_logging(log_level=settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)


async def main() -> None:
    """Initializes bot, clears conflicting webhooks, and starts single-process polling."""
    logger.info("Starting Telegram Bot Long Polling Runner...", bot_token=settings.TELEGRAM_BOT_TOKEN.get_secret_value()[:10])
    bot, dp = create_bot_and_dispatcher()

    # Clear lingering webhooks to prevent conflict errors
    await bot.delete_webhook(drop_pending_updates=True)
    bot_info = await bot.get_me()
    logger.info("Bot Connection Established", bot_name=bot_info.first_name, username=f"@{bot_info.username}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
