"""Health Check Command Router."""

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import settings

router = Router(name="health_router")
logger = structlog.get_logger(__name__)


@router.message(Command("health"))
async def handle_health(message: Message) -> None:
    """Handles /health command inspecting system operational status.

    Checks application environment mode and returns status diagnostic.
    """
    health_text = (
        "🟢 *System Operational Status*\n\n"
        f"• *Status:* Healthy\n"
        f"• *Environment:* `{settings.APP_ENV}`\n"
        f"• *Model:* `{settings.GEMINI_MODEL_NAME}`"
    )
    await message.answer(text=health_text, parse_mode="Markdown")
