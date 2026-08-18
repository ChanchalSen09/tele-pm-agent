"""Unit tests for Database ORM Models, Repositories, and AsyncUnitOfWork."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    ConversationModel,
    MessageModel,
    UserModel,
)
from app.infrastructure.database.repositories import (
    AsyncUnitOfWork,
    ConversationRepository,
    MessageRepository,
    UserRepository,
)


@pytest.fixture
async def db_session() -> AsyncSession:  # type: ignore[misc]
    """Fixture providing an in-memory SQLite AsyncSession for isolated tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def session_factory():
    """Fixture providing an in-memory SQLite SessionFactory for UnitOfWork tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    yield factory
    asyncio.run(engine.dispose())


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession) -> None:
    """Verifies UserRepository save and lookup by Telegram ID."""
    repo = UserRepository(db_session)
    user = UserModel(
        telegram_id=987654321,
        username="alice_test",
        first_name="Alice",
    )
    saved_user = await repo.save(user)
    assert saved_user.id is not None

    fetched = await repo.get_by_telegram_id(987654321)
    assert fetched is not None
    assert fetched.first_name == "Alice"
    assert fetched.username == "alice_test"


@pytest.mark.asyncio
async def test_conversation_repository_active_thread(db_session: AsyncSession) -> None:
    """Verifies ConversationRepository active thread retrieval and archiving."""
    user_repo = UserRepository(db_session)
    conv_repo = ConversationRepository(db_session)

    user = await user_repo.save(UserModel(telegram_id=12345, first_name="Bob"))

    conv1 = await conv_repo.save(ConversationModel(user_id=user.id, title="Thread 1"))
    active_conv = await conv_repo.get_active_by_user_id(user.id)
    assert active_conv is not None
    assert active_conv.id == conv1.id

    # Archive thread
    await conv_repo.archive_all_active_by_user_id(user.id)
    archived_conv = await conv_repo.get_active_by_user_id(user.id)
    assert archived_conv is None


@pytest.mark.asyncio
async def test_message_repository_sequence_and_history(
    db_session: AsyncSession,
) -> None:
    """Verifies MessageRepository sequence generation and chronological retrieval."""
    user_repo = UserRepository(db_session)
    conv_repo = ConversationRepository(db_session)
    msg_repo = MessageRepository(db_session)

    user = await user_repo.save(UserModel(telegram_id=999, first_name="Charlie"))
    conv = await conv_repo.save(ConversationModel(user_id=user.id))

    seq1 = await msg_repo.get_next_sequence_number(conv.id)
    assert seq1 == 1
    await msg_repo.save(
        MessageModel(
            conversation_id=conv.id,
            sequence_number=seq1,
            sender_role="user",
            content="Hello",
        )
    )

    seq2 = await msg_repo.get_next_sequence_number(conv.id)
    assert seq2 == 2
    await msg_repo.save(
        MessageModel(
            conversation_id=conv.id,
            sequence_number=seq2,
            sender_role="assistant",
            content="Hi Charlie!",
        )
    )

    recent = await msg_repo.get_recent_by_conversation(conv.id, limit=10)
    assert len(recent) == 2
    assert recent[0].sequence_number == 1
    assert recent[0].content == "Hello"
    assert recent[1].sequence_number == 2
    assert recent[1].content == "Hi Charlie!"


@pytest.mark.asyncio
async def test_unit_of_work_commit(session_factory) -> None:
    """Verifies AsyncUnitOfWork context manager commits multi-repository transactions."""
    async with AsyncUnitOfWork(session_factory) as uow:
        assert uow.users is not None
        assert uow.conversations is not None

        user = await uow.users.save(UserModel(telegram_id=777, first_name="Dave"))
        await uow.conversations.save(
            ConversationModel(user_id=user.id, title="Dave Thread")
        )

    # Verify data persisted across context exit
    async with AsyncUnitOfWork(session_factory) as uow:
        assert uow.users is not None
        fetched_user = await uow.users.get_by_telegram_id(777)
        assert fetched_user is not None
        assert fetched_user.first_name == "Dave"


@pytest.mark.asyncio
async def test_unit_of_work_rollback_on_exception(session_factory) -> None:
    """Verifies AsyncUnitOfWork automatically rolls back on exception."""
    try:
        async with AsyncUnitOfWork(session_factory) as uow:
            assert uow.users is not None
            await uow.users.save(UserModel(telegram_id=888, first_name="Eve"))
            raise RuntimeError("Forced Transaction Failure")
    except RuntimeError:
        pass

    # Verify rollback prevented persistence
    async with AsyncUnitOfWork(session_factory) as uow:
        assert uow.users is not None
        fetched_user = await uow.users.get_by_telegram_id(888)
        assert fetched_user is None
