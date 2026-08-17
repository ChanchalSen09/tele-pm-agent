"""Natural Language PM Action Execution Engine.

Parses plain-text user intent (task creation, status updates, status summary, check-ins)
and executes database operations without forcing users to remember slash commands.
"""

import re
from dataclasses import dataclass

import structlog

from app.core.cache import default_task_board_cache
from app.infrastructure.database.models.models import TaskModel
from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class NaturalPMResult:
    """Dataclass holding result text and action status of natural PM execution."""

    response_text: str
    action_type: str


async def parse_and_execute_natural_intent(
    user_text: str,
    chat_id: int | None,
    creator_id: int,
    uow: AsyncUnitOfWork,
) -> NaturalPMResult | None:
    """Evaluates plain text user intent and executes corresponding PM DB actions if matched."""
    if not user_text:
        return None

    text_lower = user_text.lower().strip()

    # 1. Natural Task Creation Intent
    # Matches patterns like: "create task fix login @alex", "add task update database", "new task: deploy server"
    create_match = re.search(
        r"^(please\s+)?(create|add|new)\s+(a\s+)?task[:\s]+(.+)$",
        text_lower,
        re.IGNORECASE,
    )
    if create_match:
        payload = create_match.group(4).strip()
        if payload.lower().startswith("to "):
            payload = payload[3:].strip()
        words = payload.split()
        assignee = None
        title_words = []

        for w in words:
            if w.startswith("@"):
                assignee = w.lstrip("@")
            else:
                title_words.append(w)

        title = " ".join(title_words) or "New Task"

        assert uow.tasks is not None
        task = TaskModel(
            title=title.capitalize(),
            assignee_username=assignee,
            status="TODO",
            created_by_telegram_id=creator_id,
            telegram_chat_id=chat_id,
        )
        saved_task = await uow.tasks.save(task)

        # Invalidate task board cache for this chat
        default_task_board_cache.invalidate(chat_id)

        assignee_str = f" to @{assignee}" if assignee else ""
        reply_text = (
            f"✅ *Got it! I've created the task:*\n\n"
            f"📌 *ID*: `{str(saved_task.id)[:8]}`\n"
            f"📝 *Title*: {saved_task.title}\n"
            f"👤 *Assigned*: {assignee_str or 'Unassigned'}\n"
            f"🚦 *Status*: `TODO`"
        )
        logger.info(
            "Natural PM Engine Created Task",
            task_id=str(saved_task.id),
            chat_id=chat_id,
        )
        return NaturalPMResult(response_text=reply_text, action_type="CREATE_TASK")

    # 2. Natural Task Status Update / Close Intent
    # Matches patterns like: "mark task 5d02ccee as done", "set task 5d02ccee to in_progress", "close task 5d02ccee"
    update_match = re.search(
        r"(mark|set|update|close|complete)\s+(task\s+)?([a-f0-9]{8,36})\s+(as|to|is|status\s+to)?\s*(todo|in_progress|in\s+progress|blocked|done|completed)",
        text_lower,
        re.IGNORECASE,
    )
    if update_match:
        task_id = update_match.group(3).strip()
        raw_status = update_match.group(5).strip().upper()
        if raw_status in ("DONE", "COMPLETED"):
            target_status = "DONE"
        elif "PROGRESS" in raw_status:
            target_status = "IN_PROGRESS"
        else:
            target_status = raw_status

        assert uow.tasks is not None
        task = await uow.tasks.update_status(task_id, target_status, chat_id=chat_id)
        if not task:
            reply_text = f"❌ I couldn't find a task with ID prefix `{task_id}` in this group."
        else:
            # Invalidate task board cache for this chat
            default_task_board_cache.invalidate(chat_id)
            status_emoji = "🟢" if target_status == "DONE" else "🟡"
            reply_text = (
                f"🔄 *Updated Task Status!*\n\n"
                f"📌 *ID*: `{str(task.id)[:8]}`\n"
                f"📝 *Title*: {task.title}\n"
                f"👤 *Assigned*: @{task.assignee_username or 'Unassigned'}\n"
                f"🚦 *Status*: `{task.status}` {status_emoji}"
            )
        logger.info(
            "Natural PM Engine Updated Task",
            task_id=task_id,
            new_status=target_status,
            chat_id=chat_id,
        )
        return NaturalPMResult(response_text=reply_text, action_type="UPDATE_TASK")

    # 3. Natural Task Board Request Intent
    # Matches patterns like: "show task board", "show tasks", "list tasks", "what tasks exist"
    board_match = re.search(
        r"^(show|list|view|get)\s+.*(tasks|task\s+board)",
        text_lower,
        re.IGNORECASE,
    )
    if board_match:
        cached_text = default_task_board_cache.get(chat_id)
        if cached_text:
            return NaturalPMResult(response_text=cached_text, action_type="LIST_TASKS_CACHED")

        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)
        if not tasks:
            reply_text = "📋 *Project Task Board*\n\nNo active tasks found for this group yet! Just tell me: *'Create a task <title> @assignee'* to add one."
        else:
            todo_tasks = [t for t in tasks if t.status == "TODO"]
            in_progress = [t for t in tasks if t.status == "IN_PROGRESS"]
            blocked = [t for t in tasks if t.status == "BLOCKED"]
            done = [t for t in tasks if t.status == "DONE"]

            lines = ["📋 *Project Task Board*\n"]
            if in_progress:
                lines.append("🟡 *IN PROGRESS*:")
                for t in in_progress:
                    assignee = (
                        f" (@{t.assignee_username})" if t.assignee_username else ""
                    )
                    lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
                lines.append("")

            if todo_tasks:
                lines.append("⚪ *TO DO*:")
                for t in todo_tasks:
                    assignee = (
                        f" (@{t.assignee_username})" if t.assignee_username else ""
                    )
                    lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
                lines.append("")

            if blocked:
                lines.append("🔴 *BLOCKED*:")
                for t in blocked:
                    assignee = (
                        f" (@{t.assignee_username})" if t.assignee_username else ""
                    )
                    lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
                lines.append("")

            if done:
                lines.append("🟢 *DONE*:")
                for t in done:
                    assignee = (
                        f" (@{t.assignee_username})" if t.assignee_username else ""
                    )
                    lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")

            reply_text = "\n".join(lines)

        default_task_board_cache.set(chat_id, reply_text)
        return NaturalPMResult(response_text=reply_text, action_type="LIST_TASKS")

    # 4. Natural Sprint Status Summary Request
    # Matches: "show status", "sprint status", "project status", "give me status"
    status_match = re.search(
        r"^(show|view|get|give\s+me)\s+.*(sprint|project)\s+status",
        text_lower,
        re.IGNORECASE,
    )
    if status_match:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)
        total = len(tasks)
        if total == 0:
            reply_text = "📊 *Project Status*: No tasks created yet for this group."
        else:
            done_count = sum(1 for t in tasks if t.status == "DONE")
            prog_count = sum(1 for t in tasks if t.status == "IN_PROGRESS")
            todo_count = sum(1 for t in tasks if t.status == "TODO")
            block_count = sum(1 for t in tasks if t.status == "BLOCKED")
            completion_pct = int((done_count / total) * 100)

            reply_text = (
                f"📊 *Project Status Summary*\n\n"
                f"📈 *Sprint Completion*: {completion_pct}%\n"
                f"• Total Tasks: `{total}`\n"
                f"• 🟢 Done: `{done_count}`\n"
                f"• 🟡 In Progress: `{prog_count}`\n"
                f"• ⚪ To Do: `{todo_count}`\n"
                f"• 🔴 Blocked: `{block_count}`"
            )
        return NaturalPMResult(response_text=reply_text, action_type="STATUS_SUMMARY")

    return None
