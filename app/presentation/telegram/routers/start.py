"""Start, Help, and Commands Directory Router."""

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
        "💡 *Quick Commands:*\n"
        "• `/tasks` - View task board\n"
        "• `/create_task <title> [@assignee]` - Create a task\n"
        "• `/update_task <id> <status>` - Update task status\n"
        "• `/close_task <id>` - Complete a task\n"
        "• `/status` - Sprint status report\n"
        "• `/pull_updates` - Request team status updates\n"
        "• `/commands` - View all available commands\n\n"
        "Tag `@agent_sen_09_bot` in your group or send a message to begin!"
    )
    await message.answer(text=welcome_text, parse_mode="Markdown")


@router.message(Command("commands"))
@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Handles /help and /commands displaying complete command directory."""
    help_text = (
        "📜 *Complete Agentic Project Manager Commands Directory*\n\n"
        "📌 *Task Management:*\n"
        "• `/tasks` - Display project task board (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`)\n"
        "• `/create_task <title> [@assignee]` - Create and assign a task\n"
        "• `/update_task <id> <STATUS>` - Update status (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`)\n"
        "• `/close_task <id>` (or `/task_done`) - Mark task completed (`DONE`)\n\n"
        "📊 *Tracking & Progress:*\n"
        "• `/status` - Generate sprint completion summary and task metrics\n"
        "• `/pull_updates` - Actively tag assigned members and request status check-in\n\n"
        "⚙️ *System & Information:*\n"
        "• `/start` - Display onboarding guide\n"
        "• `/commands` - View this full command directory\n"
        "• `/help` - Help overview\n"
        "• `/health` - Inspect system diagnostic health\n\n"
        "💡 *Tip*: Tag `@agent_sen_09_bot` in any group to ask questions about project tasks!"
    )
    await message.answer(text=help_text, parse_mode="Markdown")
