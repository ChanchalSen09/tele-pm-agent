"""Telegram Foundation Command Handlers (/start, /help, /reset)."""

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="foundation_commands_router")
logger = structlog.get_logger(__name__)


@router.message(CommandStart())
async def handle_start_command(message: Message) -> None:
    """Handles /start command onboarding greeting."""
    user_name = message.from_user.first_name if message.from_user else "there"
    welcome_text = (
        f"👋 Hello, *{user_name}*! Welcome to the Telegram AI Assistant.\n\n"
        "I am powered by Google Gemini and Clean Architecture.\n\n"
        "💡 *Available Commands:*\n"
        "• `/start` - Display this welcome greeting\n"
        "• `/help` - View usage guide and capabilities\n"
        "• `/reset` - Clear active context window\n\n"
        "Send me any text question to begin!"
    )
    await message.answer(text=welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def handle_help_command(message: Message) -> None:
    """Handles /help command capability overview."""
    help_text = (
        "📖 *Help & Usage Instructions*\n\n"
        "Simply type any plain text message to receive an intelligent response.\n\n"
        "• Use `/reset` if you want to clear conversation memory.\n"
        "• Media and stickers are currently disabled."
    )
    await message.answer(text=help_text, parse_mode="Markdown")


@router.message(Command("reset"))
async def handle_reset_command(message: Message) -> None:
    """Handles /reset command thread context clearing."""
    await message.answer(
        text="🧹 *Conversation context reset!* Starting a fresh thread.",
        parse_mode="Markdown",
    )
