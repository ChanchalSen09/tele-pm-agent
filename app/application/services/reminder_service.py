"""Background Reminder Service for Due Dates and Gentle Task Check-ins."""

from datetime import datetime, timezone

import structlog
from aiogram import Bot
from sqlalchemy import select

from app.infrastructure.database.models.models import TaskModel

logger = structlog.get_logger(__name__)


async def check_and_send_due_task_reminders(bot: Bot, session_factory: any) -> int:
    """Queries tasks due soon or overdue and sends reminders to Telegram chats/assignees."""
    reminders_sent = 0
    now = datetime.now(timezone.utc)

    try:
        async with session_factory() as session:
            stmt = select(TaskModel).where(
                TaskModel.deleted_at.is_(None),
                TaskModel.status.in_(["TODO", "IN_PROGRESS", "BLOCKED"]),
                TaskModel.due_date.is_not(None),
                TaskModel.due_date <= now,
            )
            result = await session.execute(stmt)
            due_tasks = result.scalars().all()

            for task in due_tasks:
                if not task.telegram_chat_id:
                    continue

                assignee_tag = (
                    f"@{task.assignee_username}" if task.assignee_username else "team"
                )
                msg_text = (
                    f"⏰ *Task Due Date Reminder*\n\n"
                    f"Hey {assignee_tag}! The task **{task.title}** (`{str(task.id)[:8]}`) is now due.\n"
                    f"Status: `{task.status}` | Priority: `{task.priority}`\n\n"
                    f"Please update the team when you get a chance!"
                )
                try:
                    await bot.send_message(
                        chat_id=task.telegram_chat_id, text=msg_text, parse_mode="HTML"
                    )
                    reminders_sent += 1
                except Exception as send_err:
                    logger.warning(
                        "Failed to dispatch Telegram due date reminder",
                        task_id=str(task.id),
                        error=str(send_err),
                    )

        if reminders_sent > 0:
            logger.info("Sent due date reminders", count=reminders_sent)

    except Exception as exc:
        logger.error("Error executing due date reminder check", error=str(exc))

    return reminders_sent
