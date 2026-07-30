# ruff: noqa: PLR2004
"""End-to-End Integration Tests verifying full pipeline flow."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.dtos.conversation import UserMessageInputDTO
from app.application.services.conversation_service import ConversationService
from app.application.services.prompt_builder import PromptBuilder
from app.domain.interfaces.llm import ILLMProvider
from app.infrastructure.database.base import Base
from app.infrastructure.database.repositories import AsyncUnitOfWork


@pytest.fixture
def sqlite_session_factory():
    """Fixture providing in-memory SQLite session factory for end-to-end testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    yield factory
    asyncio.run(engine.dispose())


@pytest.mark.asyncio
async def test_end_to_end_pipeline_with_persistence(
    mock_llm_provider: ILLMProvider, sqlite_session_factory
) -> None:
    """Verifies complete end-to-end pipeline: Input -> Prompt Builder -> Gemini -> Repository -> Response."""
    uow = AsyncUnitOfWork(sqlite_session_factory)
    prompt_builder = PromptBuilder()
    service = ConversationService(
        llm_provider=mock_llm_provider,
        prompt_builder=prompt_builder,
        unit_of_work=uow,
    )

    input_dto = UserMessageInputDTO(
        user_id="user_telegram_123",
        user_text="Explain async architecture in Python",
        correlation_id="corr_e2e_789",
    )

    telegram_id = 987654321
    user_info = {
        "username": "alice_dev",
        "first_name": "Alice",
        "last_name": "Developer",
    }

    # Turn 1
    response = await service.process_user_message(
        input_dto=input_dto,
        telegram_id=telegram_id,
        user_info=user_info,
    )

    assert response.response_text == "Mocked AI response for testing."
    assert response.total_tokens == 25
    assert response.model_name == "mock-gemini-model"

    # Verify Persistence in DB across transactional UoW bounds
    async with AsyncUnitOfWork(sqlite_session_factory) as verify_uow:
        assert verify_uow.users is not None
        assert verify_uow.conversations is not None
        assert verify_uow.messages is not None

        # Check User Record
        db_user = await verify_uow.users.get_by_telegram_id(telegram_id)
        assert db_user is not None
        assert db_user.first_name == "Alice"
        assert db_user.username == "alice_dev"

        # Check Active Conversation Record
        db_conv = await verify_uow.conversations.get_active_by_user_id(db_user.id)
        assert db_conv is not None
        assert db_conv.total_tokens_used == 25

        # Check Messages Record (Turn 1: User message seq=1, Assistant message seq=2)
        db_messages = await verify_uow.messages.get_recent_by_conversation(db_conv.id)
        assert len(db_messages) == 2
        assert db_messages[0].sequence_number == 1
        assert db_messages[0].sender_role == "user"
        assert db_messages[0].content == "Explain async architecture in Python"

        assert db_messages[1].sequence_number == 2
        assert db_messages[1].sender_role == "assistant"
        assert db_messages[1].content == "Mocked AI response for testing."

    # Turn 2: Continue Conversation in same thread
    turn2_input = UserMessageInputDTO(
        user_id="user_telegram_123",
        user_text="Can you give me a code example?",
        correlation_id="corr_e2e_790",
    )

    turn2_response = await service.process_user_message(
        input_dto=turn2_input,
        telegram_id=telegram_id,
        user_info=user_info,
    )

    assert turn2_response.response_text == "Mocked AI response for testing."

    # Verify Turn 2 accumulated history in DB
    async with AsyncUnitOfWork(sqlite_session_factory) as verify_uow:
        assert verify_uow.conversations is not None
        assert verify_uow.messages is not None

        db_conv = await verify_uow.conversations.get_active_by_user_id(db_user.id)
        assert db_conv is not None
        assert db_conv.total_tokens_used == 50  # 25 + 25 tokens

        db_messages = await verify_uow.messages.get_recent_by_conversation(db_conv.id)
        assert len(db_messages) == 4
        assert db_messages[2].sequence_number == 3
        assert db_messages[3].sequence_number == 4
