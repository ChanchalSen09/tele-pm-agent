"""Start and Help Command Router."""

import structlog
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start_router")
logger = structlog.get_logger(__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handles /start command onboarding greeting."""
    user_name = message.from_user.first_name if message.from_user else "there"
    welcome_text = (
        f"📋 Hello, *{user_name}*! Welcome to your **Agentic Project Manager**.\n\n"
        "I am built to manage tasks, track sprint progress, and pull status updates from your team on Telegram.\n\n"
        "💡 *Project Manager Commands:*\n"
        "• `/tasks` - Display project task board\n"
        "• `/create_task <title> [@assignee]` - Create a task\n"
        "• `/status` - Generate project status report\n"
        "• `/pull_updates` - Request task updates from assigned members\n"
        "• `/health` - Inspect system diagnostic status\n\n"
        "Mention me (`@agent_sen_09_bot`) in your group or send a message to begin!"
    )
    await message.answer(text=welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handles /help command displaying system capabilities and rules."""
    help_text = (
        "📖 *Agentic Project Manager Capabilities*\n\n"
        "• *Task Management*: Create, assign, track, and complete sprint tasks.\n"
        "• *Group Coordination*: Mention `@agent_sen_09_bot` in any group to manage project items.\n"
        "• *Commands*:\n"
        "  - `/tasks`: List all active project tasks\n"
        "  - `/create_task <title> [@assignee]`: Add a project task\n"
        "  - `/status`: Project status report\n"
        "  - `/pull_updates`: Pull status from assigned team members\n"
        "  - `/health`: System status"
    )
    await message.answer(text=help_text, parse_mode="Markdown")
