"""Async Unit of Work Pattern for Atomic Multi-Repository Transactional Bounds."""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing_extensions import Self

from app.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.infrastructure.database.repositories.message_repository import (
    MessageRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository


class AsyncUnitOfWork:
    """Context manager encapsulating async database sessions and transactional bounds."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self.users: UserRepository | None = None
        self.conversations: ConversationRepository | None = None
        self.messages: MessageRepository | None = None

    async def __aenter__(self) -> Self:
        """Enters async transaction context and initializes repository bounds."""
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.conversations = ConversationRepository(self.session)
        self.messages = MessageRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exits async transaction context, committing on success or rolling back on exception."""
        if not self.session:
            return

        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

        await self.session.close()

    async def commit(self) -> None:
        """Commits current database transaction."""
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        """Rolls back current database transaction."""
        if self.session:
            await self.session.rollback()
