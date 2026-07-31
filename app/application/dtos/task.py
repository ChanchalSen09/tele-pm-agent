"""Task Data Transfer Objects (DTOs)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class TaskCreateDTO:
    """DTO for creating a new project task."""

    title: str
    description: str | None = None
    assignee_username: str | None = None
    created_by_telegram_id: int = 0


@dataclass(frozen=True)
class TaskUpdateStatusDTO:
    """DTO for updating task status."""

    task_id: str
    new_status: str


@dataclass(frozen=True)
class TaskResponseDTO:
    """DTO representing serialized task output."""

    id: UUID
    title: str
    description: str | None
    assignee_username: str | None
    status: str
    created_at: datetime
