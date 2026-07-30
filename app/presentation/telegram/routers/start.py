"""Start and Help Command Router."""

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start_router")
logger = structlog.get_logger(__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handles /start command onboarding greeting.

    Validates incoming user metadata, formats onboarding greeting, and replies.
    """
    user_name = message.from_user.first_name if message.from_user else "there"
    welcome_text = (
        f"👋 Hello, *{user_name}*! Welcome to the Telegram AI Assistant.\n\n"
        "I am built with aiogram 3.x and Clean Architecture.\n\n"
        "💡 *Available Commands:*\n"
        "• `/start` - Display this onboarding guide\n"
        "• `/help` - View usage instructions and capabilities\n"
        "• `/health` - Inspect system health and status\n\n"
        "Send me a message to begin!"
    )
    await message.answer(text=welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handles /help command displaying system capabilities and rules.

    Formats capability text and replies to user.
    """
    help_text = (
        "📖 *Help & Capabilities*\n\n"
        "• *Conversational AI*: Send plain text questions to get answers.\n"
        "• *Commands*:\n"
        "  - `/start`: Onboarding overview\n"
        "  - `/help`: Detailed help text\n"
        "  - `/health`: System diagnostic check"
    )
    await message.answer(text=help_text, parse_mode="Markdown")
