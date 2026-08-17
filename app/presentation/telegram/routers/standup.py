"""Telegram Standup Router handling daily team standups and retrospective reports."""

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork
from app.infrastructure.database.session import AsyncSessionFactory
from app.presentation.telegram.routers.chat import send_safe_reply

router = Router(name="standup_router")
logger = structlog.get_logger(__name__)


@router.message(Command("standup"))
async def handle_standup_command(message: Message) -> None:
    """Triggers an interactive daily standup prompt for team members in current group."""
    chat_id = message.chat.id
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)

    open_tasks = [t for t in tasks if t.status in ("TODO", "IN_PROGRESS", "BLOCKED")]
    done_tasks = [t for t in tasks if t.status == "DONE"]

    lines = [
        "☀️ <b>Daily Team Standup</b>\n",
        "Hey team! Let's do a quick daily standup check-in.",
        "Please reply with:\n",
        "1️⃣ <b>What did you accomplish yesterday?</b>",
        "2️⃣ <b>What are you working on today?</b>",
        "3️⃣ <b>Any blockers or help needed?</b>\n",
    ]

    if open_tasks:
        lines.append(f"📋 Currently tracking <b>{len(open_tasks)}</b> active tasks on our board.")
    if done_tasks:
        lines.append(f"🎉 <b>{len(done_tasks)}</b> tasks completed so far in this sprint!")

    await send_safe_reply(message, "\n".join(lines))
