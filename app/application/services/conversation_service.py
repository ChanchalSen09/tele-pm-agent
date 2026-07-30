"""Conversation Application Service integrating Prompt Builder, Gemini Adapter, and Repository Unit of Work."""

from collections import defaultdict
from typing import Any

import structlog

from app.application.dtos.conversation import (
    ConversationResponseDTO,
    UserMessageInputDTO,
)
from app.application.services.prompt_builder import PromptBuilder
from app.core.exceptions import ValidationException
from app.core.security import sanitize_input_text
from app.domain.interfaces.llm import ILLMProvider, LLMMessage
from app.infrastructure.database.models import (
    AIResponseModel,
    ConversationModel,
    MessageModel,
    UserModel,
)
from app.infrastructure.database.repositories import AsyncUnitOfWork

logger = structlog.get_logger(__name__)

MAX_MESSAGE_LENGTH = 4000


class ConversationService:
    """Orchestrates the end-to-end pipeline: Telegram Input -> Prompt Builder -> Gemini -> Repository -> Response."""

    def __init__(
        self,
        llm_provider: ILLMProvider,
        prompt_builder: PromptBuilder | None = None,
        unit_of_work: AsyncUnitOfWork | None = None,
        max_context_turns: int = 10,
    ) -> None:
        self.llm_provider = llm_provider
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.unit_of_work = unit_of_work
        self.max_context_turns = max_context_turns
        self._user_context_store: dict[str, list[LLMMessage]] = defaultdict(list)

    async def process_user_message(
        self,
        input_dto: UserMessageInputDTO,
        telegram_id: int | None = None,
        user_info: dict[str, Any] | None = None,
    ) -> ConversationResponseDTO:
        """Executes full conversational turn pipeline across Domain, AI, and Persistence layers."""
        raw_text = input_dto.user_text or ""
        if len(raw_text) > MAX_MESSAGE_LENGTH:
            raise ValidationException(
                f"Message text exceeds maximum length limit of {MAX_MESSAGE_LENGTH} characters."
            )

        sanitized_text = sanitize_input_text(raw_text)
        if not sanitized_text:
            raise ValidationException("User message text cannot be empty.")

        # Execute persistence workflow if Unit of Work is injected
        if self.unit_of_work and telegram_id:
            return await self._process_with_persistence(
                input_dto=input_dto,
                telegram_id=telegram_id,
                sanitized_text=sanitized_text,
                user_info=user_info or {},
            )

        # In-memory execution fallback (pure service without DB)
        return await self._process_in_memory(
            input_dto=input_dto, sanitized_text=sanitized_text
        )

    async def _process_with_persistence(
        self,
        input_dto: UserMessageInputDTO,
        telegram_id: int,
        sanitized_text: str,
        user_info: dict[str, Any],
    ) -> ConversationResponseDTO:
        """Executes pipeline with PostgreSQL persistence transactional bounds."""
        assert self.unit_of_work is not None

        async with self.unit_of_work as uow:
            assert uow.users is not None
            assert uow.conversations is not None
            assert uow.messages is not None

            # 1. Resolve or Provision User Entity
            user = await uow.users.get_by_telegram_id(telegram_id)
            if not user:
                user = await uow.users.save(
                    UserModel(
                        telegram_id=telegram_id,
                        username=user_info.get("username"),
                        first_name=user_info.get("first_name", "User"),
                        last_name=user_info.get("last_name"),
                    )
                )

            # 2. Resolve Active Conversation Thread
            conversation = await uow.conversations.get_active_by_user_id(user.id)
            if not conversation:
                conversation = await uow.conversations.save(
                    ConversationModel(user_id=user.id, title="New Conversation")
                )

            # 3. Fetch Recent Message History
            recent_db_messages = await uow.messages.get_recent_by_conversation(
                conversation.id, limit=self.max_context_turns
            )
            history_messages = [
                LLMMessage(role=msg.sender_role, content=msg.content)
                for msg in recent_db_messages
            ]

            # 4. Prompt Builder: Construct System Persona & Token Optimized Payload
            payload = self.prompt_builder.build_prompt_payload(
                user_text=sanitized_text,
                history=history_messages,
                variables={
                    "user_name": user.first_name,
                    "tier": user.tier,
                },
            )

            # 5. Gemini Generation Call
            llm_response = await self.llm_provider.generate_completion(
                system_prompt=payload.system_prompt,
                history=payload.history,
                user_prompt=sanitized_text,
            )

            # 6. Repository Atomic Writes
            user_seq = await uow.messages.get_next_sequence_number(conversation.id)
            await uow.messages.save(
                MessageModel(
                    conversation_id=conversation.id,
                    sequence_number=user_seq,
                    sender_role="user",
                    content=sanitized_text,
                )
            )

            asst_seq = user_seq + 1
            asst_msg = await uow.messages.save(
                MessageModel(
                    conversation_id=conversation.id,
                    sequence_number=asst_seq,
                    sender_role="assistant",
                    content=llm_response.generated_text,
                )
            )

            # Persist execution metrics
            uow.session.add(  # type: ignore[union-attr]
                AIResponseModel(
                    message_id=asst_msg.id,
                    model_name=llm_response.model_name,
                    prompt_tokens=llm_response.prompt_tokens,
                    completion_tokens=llm_response.completion_tokens,
                    total_tokens=llm_response.total_tokens,
                    latency_ms=llm_response.latency_ms,
                    finish_reason=llm_response.finish_reason,
                )
            )

            conversation.total_tokens_used += llm_response.total_tokens
            await uow.conversations.save(conversation)

            logger.info(
                "End-to-End Pipeline Turn Persisted",
                user_id=user.id,
                conversation_id=conversation.id,
                total_tokens=llm_response.total_tokens,
                correlation_id=input_dto.correlation_id,
            )

            return ConversationResponseDTO(
                response_text=llm_response.generated_text,
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
                latency_ms=llm_response.latency_ms,
                finish_reason=llm_response.finish_reason,
                model_name=llm_response.model_name,
            )

    async def _process_in_memory(
        self,
        input_dto: UserMessageInputDTO,
        sanitized_text: str,
    ) -> ConversationResponseDTO:
        """In-memory processing fallback."""
        history = self._user_context_store[input_dto.user_id]
        if len(history) > self.max_context_turns:
            history = history[-self.max_context_turns :]

        payload = self.prompt_builder.build_prompt_payload(
            user_text=sanitized_text,
            history=history,
        )

        llm_response = await self.llm_provider.generate_completion(
            system_prompt=payload.system_prompt,
            history=payload.history,
            user_prompt=sanitized_text,
        )

        self._user_context_store[input_dto.user_id].append(
            LLMMessage(role="user", content=sanitized_text)
        )
        self._user_context_store[input_dto.user_id].append(
            LLMMessage(role="assistant", content=llm_response.generated_text)
        )
        if len(self._user_context_store[input_dto.user_id]) > self.max_context_turns:
            self._user_context_store[input_dto.user_id] = self._user_context_store[
                input_dto.user_id
            ][-self.max_context_turns :]

        return ConversationResponseDTO(
            response_text=llm_response.generated_text,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            latency_ms=llm_response.latency_ms,
            finish_reason=llm_response.finish_reason,
            model_name=llm_response.model_name,
        )

    def clear_user_context(self, user_id: str) -> None:
        """Clears active sliding context memory for a user."""
        if user_id in self._user_context_store:
            self._user_context_store[user_id].clear()
            logger.info("Cleared user conversation context memory", user_id=user_id)

    def get_user_context_length(self, user_id: str) -> int:
        """Returns the number of message turns stored in active user context."""
        return len(self._user_context_store.get(user_id, []))
