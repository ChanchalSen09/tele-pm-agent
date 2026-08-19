"""Domain Interface Contracts for Repositories (IRepository)."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class IBaseRepository(ABC, Generic[T]):
    """Generic Base Repository Interface."""

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Fetch entity by primary key ID."""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persist or update entity in data store."""
        pass

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Remove or soft-delete entity from data store."""
        pass


class IUserRepository(IBaseRepository[Any]):
    """User Repository Interface."""

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Any | None:
        """Fetch user by Telegram ID."""
        pass

    @abstractmethod
    async def list_by_chat_id(self, chat_id: int | None) -> list[Any]:
        """Fetch users participating in a specific chat."""
        pass

    @abstractmethod
    async def list_all_users(self) -> list[Any]:
        """Fetch all active users."""
        pass


class IConversationRepository(IBaseRepository[Any]):
    """Conversation Thread Repository Interface."""

    @abstractmethod
    async def get_active_by_user_id(self, user_id: UUID) -> Any | None:
        """Fetch active conversation thread for a user."""
        pass


class IMessageRepository(IBaseRepository[Any]):
    """Message Record Repository Interface."""

    @abstractmethod
    async def get_recent_by_conversation(
        self, conversation_id: UUID, limit: int = 10
    ) -> list[Any]:
        """Fetch recent sequential message turns for context window."""
        pass
