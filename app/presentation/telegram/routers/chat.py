# ruff: noqa: PLR2004
"""Telegram Chat Router handling text queries and Project Manager task management."""

import html
import re

import structlog
from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command
from aiogram.types import Message

from app.application.dtos.conversation import UserMessageInputDTO
from app.application.services.conversation_service import ConversationService
from app.application.services.standup_engine import (
    process_standup_user_update,
    trigger_group_standup,
)
from app.infrastructure.database.models.models import TaskModel
from app.infrastructure.database.repositories import AsyncUnitOfWork
from app.infrastructure.database.session import AsyncSessionFactory
from app.infrastructure.llm.gemini_client import get_gemini_client

router = Router(name="chat_router")
logger = structlog.get_logger(__name__)

# Default singleton service dependency with persistence
_conversation_service = ConversationService(
    llm_provider=get_gemini_client(),
    unit_of_work=AsyncUnitOfWork(AsyncSessionFactory),
)


@router.message(Command("standup"))
@router.message(Command("checkin"))
async def handle_standup_command(message: Message) -> None:
    """Triggers group daily standup tagging active assignees."""
    chat_id = message.chat.id
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        standup_text = await trigger_group_standup(chat_id=chat_id, uow=uow)
    await send_safe_reply(message, standup_text)


def markdown_to_telegram_html(text: str) -> str:
    """Converts standard Markdown text into Telegram-compliant HTML tags."""
    if not text:
        return ""

    code_blocks: list[str] = []
    inline_codes: list[str] = []

    def save_code_block(match: re.Match[str]) -> str:
        code_content = match.group(1) or ""
        escaped_code = html.escape(code_content.strip("\n"))
        code_blocks.append(f"<pre><code>{escaped_code}</code></pre>")
        return f"\x00CB{len(code_blocks) - 1}\x00"

    def save_inline_code(match: re.Match[str]) -> str:
        code_content = match.group(1)
        escaped_code = html.escape(code_content)
        inline_codes.append(f"<code>{escaped_code}</code>")
        return f"\x00IC{len(inline_codes) - 1}\x00"

    # Extract code blocks
    processed = re.sub(r"```(?:\w+)?\n?(.*?)```", save_code_block, text, flags=re.DOTALL)
    # Extract inline code
    processed = re.sub(r"`([^`]+)`", save_inline_code, processed)

    # HTML escape remaining prose text
    processed = html.escape(processed)

    # Convert Headers (# Header -> <b>Header</b>)
    processed = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", processed, flags=re.MULTILINE)

    # Convert Bold (**text** -> <b>text</b>)
    processed = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", processed)

    # Convert Italic (*text* -> <i>text</i>)
    processed = re.sub(r"(?<!\w)\*(.*?)\*(?!\w)", r"<i>\1</i>", processed)

    # Restore code blocks & inline code
    for i, cb in enumerate(code_blocks):
        processed = processed.replace(f"\x00CB{i}\x00", cb)
    for i, ic in enumerate(inline_codes):
        processed = processed.replace(f"\x00IC{i}\x00", ic)

    return processed


async def send_safe_reply(message: Message, text: str) -> None:
    """Safely replies to a message using Telegram HTML, falling back to Markdown and plain text."""
    # Attempt 1: Telegram HTML format
    try:
        html_text = markdown_to_telegram_html(text)
        await message.reply(text=html_text, parse_mode="HTML")
        return
    except Exception as exc:
        logger.debug("HTML reply failed, trying legacy Markdown", error=str(exc))

    # Attempt 2: Legacy Markdown format
    try:
        await message.reply(text=text, parse_mode="Markdown")
        return
    except Exception as exc:
        logger.warning("Markdown parse error, falling back to plain text", error=str(exc))

    # Attempt 3: Plain text fallback
    try:
        await message.reply(text=text)
    except Exception:
        if message.bot:
            await message.bot.send_message(chat_id=message.chat.id, text=text)


@router.message(Command("tasks"))
async def handle_tasks_list(message: Message) -> None:
    """Lists all active project tasks grouped by status for the current chat/group."""
    chat_id = message.chat.id
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)

    if not tasks:
        await send_safe_reply(
            message,
            "📋 *Project Task Board*\n\nNo active tasks found for this group. Use `/create_task <title> [@assignee]` to add a task!",
        )
        return

    todo_tasks = [t for t in tasks if t.status == "TODO"]
    in_progress = [t for t in tasks if t.status == "IN_PROGRESS"]
    blocked = [t for t in tasks if t.status == "BLOCKED"]
    done = [t for t in tasks if t.status == "DONE"]

    lines = ["📋 *Project Task Board*\n"]
    if in_progress:
        lines.append("🟡 *IN PROGRESS*:")
        for t in in_progress:
            assignee = f" (@{t.assignee_username})" if t.assignee_username else ""
            lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
        lines.append("")

    if todo_tasks:
        lines.append("⚪ *TO DO*:")
        for t in todo_tasks:
            assignee = f" (@{t.assignee_username})" if t.assignee_username else ""
            lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
        lines.append("")

    if blocked:
        lines.append("🔴 *BLOCKED*:")
        for t in blocked:
            assignee = f" (@{t.assignee_username})" if t.assignee_username else ""
            lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")
        lines.append("")

    if done:
        lines.append("🟢 *DONE*:")
        for t in done:
            assignee = f" (@{t.assignee_username})" if t.assignee_username else ""
            lines.append(f"• `{str(t.id)[:8]}`: {t.title}{assignee}")

    await send_safe_reply(message, "\n".join(lines))


@router.message(Command("create_task"))
async def handle_create_task(message: Message) -> None:
    """Creates a new task for the project linked to the active chat/group."""
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await send_safe_reply(
            message,
            "⚠️ Usage: `/create_task <task title> [@assignee]`\nExample: `/create_task Fix login API @alex`",
        )
        return

    payload = parts[1].strip()
    words = payload.split()
    assignee = None
    title_words = []

    for w in words:
        if w.startswith("@"):
            assignee = w.lstrip("@")
        else:
            title_words.append(w)

    title = " ".join(title_words) or "New Task"
    creator_id = message.from_user.id if message.from_user else 0
    chat_id = message.chat.id

    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title=title,
            assignee_username=assignee,
            status="TODO",
            created_by_telegram_id=creator_id,
            telegram_chat_id=chat_id,
        )
        saved_task = await uow.tasks.save(task)

    assignee_str = f" to @{assignee}" if assignee else ""
    reply_text = (
        f"✅ *Task Created Successfully!*\n\n"
        f"📌 *ID*: `{str(saved_task.id)[:8]}`\n"
        f"📝 *Title*: {saved_task.title}\n"
        f"👤 *Assigned*: {assignee_str or 'Unassigned'}\n"
        f"🚦 *Status*: `TODO`"
    )
    await send_safe_reply(message, reply_text)


@router.message(Command("status"))
async def handle_project_status(message: Message) -> None:
    """Generates project status summary report for current chat/group."""
    chat_id = message.chat.id
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)

    total = len(tasks)
    if total == 0:
        await send_safe_reply(message, "📊 *Project Status*: No tasks created yet for this group.")
        return

    done_count = sum(1 for t in tasks if t.status == "DONE")
    prog_count = sum(1 for t in tasks if t.status == "IN_PROGRESS")
    todo_count = sum(1 for t in tasks if t.status == "TODO")
    block_count = sum(1 for t in tasks if t.status == "BLOCKED")
    completion_pct = int((done_count / total) * 100)

    summary_text = (
        f"📊 *Project Status Summary*\n\n"
        f"📈 *Sprint Completion*: {completion_pct}%\n"
        f"• Total Tasks: `{total}`\n"
        f"• 🟢 Done: `{done_count}`\n"
        f"• 🟡 In Progress: `{prog_count}`\n"
        f"• ⚪ To Do: `{todo_count}`\n"
        f"• 🔴 Blocked: `{block_count}`\n\n"
        f"Use `/pull_updates` to ask assigned members for status!"
    )
    await send_safe_reply(message, summary_text)


@router.message(Command("pull_updates"))
async def handle_pull_updates(message: Message) -> None:
    """Actively pulls status updates from assigned team members in current group."""
    chat_id = message.chat.id
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks(chat_id=chat_id)

    open_tasks = [t for t in tasks if t.status in ("TODO", "IN_PROGRESS", "BLOCKED")]
    if not open_tasks:
        await send_safe_reply(message, "🎉 All tasks are completed for this group! No open status updates required.")
        return

    lines = ["📣 *Project Manager Status Check-In*\n"]
    tagged_members = set()

    for t in open_tasks:
        if t.assignee_username:
            tagged_members.add(f"@{t.assignee_username}")
            lines.append(f"• @{t.assignee_username}: Please reply with status for *{t.title}* (`{str(t.id)[:8]}`)")
        else:
            lines.append(f"• Unassigned: *{t.title}* (`{str(t.id)[:8]}`)")

    if tagged_members:
        lines.append(f"\nHey {' '.join(tagged_members)} — please provide a brief update on your tasks!")
    else:
        lines.append("\nTeam, please assign or update progress on the unassigned open tasks.")

    await send_safe_reply(message, "\n".join(lines))


@router.message(Command("update_task"))
async def handle_update_task(message: Message) -> None:
    """Updates status of a task by ID prefix within the current chat/group."""
    text = message.text or ""
    parts = text.split()
    if len(parts) < 3:
        await send_safe_reply(
            message,
            "⚠️ Usage: `/update_task <task_id> <STATUS>`\nAllowed Statuses: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`\nExample: `/update_task 5d02ccee IN_PROGRESS`",
        )
        return

    task_id = parts[1].strip()
    status_input = parts[2].strip().upper()
    valid_statuses = {"TODO", "IN_PROGRESS", "BLOCKED", "DONE"}
    chat_id = message.chat.id

    if status_input not in valid_statuses:
        await send_safe_reply(
            message,
            f"⚠️ Invalid status `{status_input}`. Choose from: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`",
        )
        return

    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        task = await uow.tasks.update_status(task_id, status_input, chat_id=chat_id)

    if not task:
        await send_safe_reply(message, f"❌ Task with ID prefix `{task_id}` not found in this group.")
        return

    await send_safe_reply(
        message,
        f"🔄 *Task Status Updated!*\n\n"
        f"📌 *ID*: `{str(task.id)[:8]}`\n"
        f"📝 *Title*: {task.title}\n"
        f"👤 *Assigned*: @{task.assignee_username or 'Unassigned'}\n"
        f"🚦 *New Status*: `{task.status}`",
    )


@router.message(Command("close_task"))
@router.message(Command("task_done"))
async def handle_close_task(message: Message) -> None:
    """Closes/completes a task by ID prefix within current group."""
    text = message.text or ""
    parts = text.split()
    if len(parts) < 2:
        await send_safe_reply(
            message,
            "⚠️ Usage: `/close_task <task_id>`\nExample: `/close_task 5d02ccee`",
        )
        return

    task_id = parts[1].strip()
    chat_id = message.chat.id

    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        task = await uow.tasks.update_status(task_id, "DONE", chat_id=chat_id)

    if not task:
        await send_safe_reply(message, f"❌ Task with ID prefix `{task_id}` not found in this group.")
        return

    await send_safe_reply(
        message,
        f"🎉 *Task Closed Successfully!*\n\n"
        f"📌 *ID*: `{str(task.id)[:8]}`\n"
        f"📝 *Title*: {task.title}\n"
        f"👤 *Assigned*: @{task.assignee_username or 'Unassigned'}\n"
        f"🚦 *Status*: `DONE` 🟢",
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(
    message: Message,
    conversation_service: ConversationService | None = None,
    correlation_id: str = "N/A",
) -> None:
    """Handles incoming plain text query updates from Telegram (Private & Group chats)."""
    if not message.text or not message.from_user:
        return

    user_text = message.text

    # Group & Supergroup Mention / Reply Filter
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        bot_info = await message.bot.get_me() if message.bot else None
        bot_username = bot_info.username if bot_info else None

        is_mentioned = False
        if bot_username:
            username_tag = f"@{bot_username.lower()}"
            if username_tag in message.text.lower():
                is_mentioned = True
                clean_words = [
                    w
                    for w in message.text.split()
                    if not w.lower().startswith(username_tag)
                ]
                user_text = " ".join(clean_words).strip() or message.text

        is_reply_to_bot = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and bot_info
            and message.reply_to_message.from_user.id == bot_info.id
        )

        if not (is_mentioned or is_reply_to_bot):
            return

    service = conversation_service or _conversation_service
    user_id = str(message.from_user.id)
    telegram_id = message.from_user.id
    chat_id = message.chat.id

    # Check for Standup/Progress Update Reply
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        standup_reply = await process_standup_user_update(
            user_id=telegram_id,
            username=message.from_user.username,
            user_text=user_text,
            chat_id=chat_id,
            uow=uow,
        )
        if standup_reply:
            await send_safe_reply(message, standup_reply)
            return

    user_info = {
        "username": message.from_user.username,
        "first_name": message.from_user.first_name or "User",
        "last_name": message.from_user.last_name,
    }

    input_dto = UserMessageInputDTO(
        user_id=user_id,
        user_text=user_text,
        correlation_id=correlation_id,
    )

    if message.bot:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )

    response_dto = await service.process_user_message(
        input_dto=input_dto,
        telegram_id=telegram_id,
        chat_id=chat_id,
        user_info=user_info,
    )

    await send_safe_reply(message, response_dto.response_text)
