"""Telegram Chat Router handling text queries in private and group chats via ConversationService."""

import structlog
from aiogram import F, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.types import Message

from app.application.dtos.conversation import UserMessageInputDTO
from app.application.services.conversation_service import ConversationService
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


@router.message(F.text & ~F.text.startswith("/"))
async def handle_chat_message(
    message: Message,
    conversation_service: ConversationService | None = None,
    correlation_id: str = "N/A",
) -> None:
    """Handles incoming plain text query updates from Telegram (Private & Group chats).

    Validates group mentions, triggers typing indicator, dispatches query to
    ConversationService, and returns generated Markdown response.
    """
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
                # Clean @mention tag from user prompt
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

        # Ignore messages in groups that do NOT mention or reply to the bot
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

    # Trigger typing visual indicator on Telegram UI
    if message.bot:
        await message.bot.send_chat_action(
            chat_id=message.chat.id, action=ChatAction.TYPING
        )

    response_dto = await service.process_user_message(
        input_dto=input_dto,
        telegram_id=telegram_id,
        user_info=user_info,
    )

    await message.reply(text=response_dto.response_text, parse_mode="Markdown")
