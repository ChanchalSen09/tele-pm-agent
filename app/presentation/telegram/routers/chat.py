# ruff: noqa: PLR2004
"""Telegram Chat Router handling text queries and Project Manager task management."""

import structlog
from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command
from aiogram.types import Message

from app.application.dtos.conversation import UserMessageInputDTO
from app.application.services.conversation_service import ConversationService
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


async def send_safe_reply(message: Message, text: str) -> None:
    """Safely replies to a message, falling back to plain text if Markdown parsing fails."""
    try:
        await message.reply(text=text, parse_mode="Markdown")
    except Exception as exc:
        logger.warning("Markdown parse error, falling back to plain text", error=str(exc))
        await message.reply(text=text)


@router.message(Command("tasks"))
async def handle_tasks_list(message: Message) -> None:
    """Lists all active project tasks grouped by status."""
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks()

    if not tasks:
        await send_safe_reply(
            message,
            "📋 *Project Task Board*\n\nNo active tasks found. Use `/create_task <title> [@assignee]` to add a task!",
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
    """Creates a new task for the project."""
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

    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title=title,
            assignee_username=assignee,
            status="TODO",
            created_by_telegram_id=creator_id,
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
    """Generates project status summary report."""
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks()

    total = len(tasks)
    if total == 0:
        await send_safe_reply(message, "📊 *Project Status*: No tasks created yet.")
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
    """Actively pulls status updates from assigned team members."""
    async with AsyncUnitOfWork(AsyncSessionFactory) as uow:
        assert uow.tasks is not None
        tasks = await uow.tasks.list_all_tasks()

    open_tasks = [t for t in tasks if t.status in ("TODO", "IN_PROGRESS", "BLOCKED")]
    if not open_tasks:
        await send_safe_reply(message, "🎉 All tasks are completed! No open status updates required.")
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
        user_info=user_info,
    )

    await send_safe_reply(message, response_dto.response_text)
