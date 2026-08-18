"""Proactive Standup & Direct User Check-in Engine.

Generates daily standup nudges tagging assigned team members, creates random/midday
progress check-ins on IN_PROGRESS and BLOCKED tasks, and processes updates received in group chats or private DMs.
"""

from datetime import datetime, timezone

import structlog

from app.core.cache import default_task_board_cache
from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork

logger = structlog.get_logger(__name__)


async def trigger_group_standup(chat_id: int | None, uow: AsyncUnitOfWork) -> str:
    """Generates daily standup message tagging all assigned team members with active tasks."""
    assert uow.tasks is not None
    assert uow.standups is not None

    tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)
    active_tasks = [t for t in tasks if t.status in ("TODO", "IN_PROGRESS", "BLOCKED")]

    if not active_tasks:
        return "☀️ *Daily Standup Time!*\n\nAll tasks are currently completed! Great job team! 🎉"

    # Group tasks by assignee
    assigned_map: dict[str, list[tuple[str, str, str]]] = {}
    unassigned_count = 0

    for t in active_tasks:
        short_id = str(t.id)[:8]
        if t.assignee_username:
            user = t.assignee_username.lstrip("@")
            if user not in assigned_map:
                assigned_map[user] = []
            assigned_map[user].append((short_id, t.title, t.status))
        else:
            unassigned_count += 1

    lines = [
        "☀️ *Daily Standup Time!*",
        "Please share your status update (what you completed, your goals today, and any blockers):",
        "",
    ]

    for user, user_tasks in assigned_map.items():
        lines.append(f"👤 *@ {user}*:")
        for short_id, title, status in user_tasks:
            lines.append(f"  • `{short_id}`: {title} (`{status}`)")
        lines.append("")

    if unassigned_count > 0:
        lines.append(f"📌 *Unassigned Tasks Pending*: {unassigned_count}")
        lines.append("")

    lines.append("💬 *Reply here or send me a private DM with your task updates!*")
    standup_text = "\n".join(lines)

    # Log standup entry
    if chat_id is not None:
        await uow.standups.log_checkin(
            telegram_chat_id=chat_id,
            telegram_user_id=None,
            checkin_type="DAILY_STANDUP",
            prompt_text=standup_text,
        )

    logger.info("Triggered group daily standup", chat_id=chat_id, assignees=len(assigned_map))
    return standup_text


async def trigger_midday_checkins(chat_id: int | None, uow: AsyncUnitOfWork) -> list[str]:
    """Generates random/midday check-in nudges for IN_PROGRESS and BLOCKED tasks."""
    assert uow.tasks is not None
    assert uow.standups is not None

    tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)
    target_tasks = [t for t in tasks if t.status in ("IN_PROGRESS", "BLOCKED") and t.assignee_username]

    nudges: list[str] = []
    now = datetime.now(timezone.utc)

    for task in target_tasks:
        user = task.assignee_username.lstrip("@")
        short_id = str(task.id)[:8]
        status_icon = "🔴" if task.status == "BLOCKED" else "🟡"

        nudge_text = (
            f"👋 *Mid-day Progress Check-in*\n\n"
            f"Hey @{user}! Quick check-in on task `{short_id}`: *{task.title}* {status_icon} (`{task.status}`).\n"
            f"How is it coming along? Any blockers or progress updates to share?"
        )
        nudges.append(nudge_text)

        # Update last checkin timestamp
        task.last_checkin_at = now
        await uow.standups.log_checkin(
            telegram_chat_id=chat_id or 0,
            telegram_user_id=None,
            checkin_type="MIDDAY_CHECKIN",
            prompt_text=nudge_text,
            task_id=task.id,
        )

    logger.info("Generated midday check-in nudges", chat_id=chat_id, count=len(nudges))
    return nudges


async def process_standup_user_update(
    user_id: int,
    username: str | None,
    user_text: str,
    chat_id: int | None,
    uow: AsyncUnitOfWork,
) -> str | None:
    """Processes user standup/progress update reply, updates task notes in DB, and responds."""
    if not user_text:
        return None

    assert uow.tasks is not None
    assert uow.standups is not None

    # Check if user has active tasks in this group or globally
    tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)
    user_handle = username.lstrip("@") if username else None

    matching_task = None
    if user_handle:
        for t in tasks:
            if t.assignee_username and t.assignee_username.lstrip("@").lower() == user_handle.lower():
                if t.status in ("IN_PROGRESS", "TODO", "BLOCKED"):
                    matching_task = t
                    break

    # If matching task found, update progress notes & timestamp
    if matching_task:
        matching_task.progress_notes = user_text.strip()
        matching_task.last_checkin_at = datetime.now(timezone.utc)
        default_task_board_cache.invalidate(chat_id)

        # Mark pending checkin as responded if exists
        pending = await uow.standups.get_pending_checkin(telegram_user_id=user_id, telegram_chat_id=chat_id)
        if pending:
            await uow.standups.mark_responded(pending.id, response_text=user_text)

        short_id = str(matching_task.id)[:8]
        reply_msg = (
            f"👍 *Status Update Logged!*\n\n"
            f"📌 *Task*: `{short_id}` ({matching_task.title})\n"
            f"📝 *Progress Note*: \"{user_text.strip()}\"\n"
            f"🚦 *Current Status*: `{matching_task.status}`"
        )
        logger.info(
            "Logged standup progress note",
            task_id=short_id,
            user=username,
            chat_id=chat_id,
        )
        return reply_msg

    return None
