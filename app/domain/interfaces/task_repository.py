"""Task Repository Interface definition for Domain Driven Design."""

from abc import ABC, abstractmethod
from typing import Any

from app.domain.interfaces.repository import IBaseRepository


class ITaskRepository(IBaseRepository[Any], ABC):
    """Abstract interface defining Task domain entity persistence operations."""

    @abstractmethod
    async def get_by_title(self, title: str, chat_id: int | None = None) -> Any | None:
        """Retrieves task entity matching target title."""

    @abstractmethod
    async def list_all_tasks(self, chat_id: int | None = None) -> list[Any]:
        """Retrieves all active project tasks ordered by status and creation time for a specific chat/group."""

    @abstractmethod
    async def list_by_assignee(
        self, assignee_username: str, chat_id: int | None = None
    ) -> list[Any]:
        """Retrieves tasks assigned to a specific username."""

    @abstractmethod
    async def list_by_status(
        self, status: str, chat_id: int | None = None
    ) -> list[Any]:
        """Retrieves tasks matching target status (TODO, IN_PROGRESS, BLOCKED, DONE)."""

    @abstractmethod
    async def update_status(
        self, task_id: str, new_status: str, chat_id: int | None = None
    ) -> Any | None:
        """Updates task status by task ID."""

