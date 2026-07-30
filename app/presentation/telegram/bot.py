"""Telegram Bot Initialization and Configuration."""

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings
from app.presentation.telegram.dispatcher import setup_dispatcher

logger = structlog.get_logger(__name__)


def create_bot() -> Bot:
    """Factory creating and configuring the Aiogram Bot instance."""
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """Factory creating Bot and Dispatcher pair configured for application ingress."""
    bot = create_bot()
    dp = setup_dispatcher()
    return bot, dp
