"""SQLAlchemy Async Task Repository implementation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.task_repository import ITaskRepository
from app.infrastructure.database.models.models import TaskModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class TaskRepository(SQLAlchemyBaseRepository[TaskModel], ITaskRepository):
    """Repository managing TaskModel entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=TaskModel)

    async def get_by_title(
        self, title: str, chat_id: int | None = None
    ) -> TaskModel | None:
        """Retrieves task matching title."""
        conditions = [TaskModel.title == title, TaskModel.deleted_at.is_(None)]
        if chat_id is not None:
            conditions.append(TaskModel.telegram_chat_id == chat_id)

        stmt = select(TaskModel).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_tasks(self, chat_id: int | None = None) -> list[TaskModel]:
        """Retrieves all active project tasks ordered by creation date for a target chat_id."""
        conditions = [TaskModel.deleted_at.is_(None)]
        if chat_id is not None:
            conditions.append(TaskModel.telegram_chat_id == chat_id)

        stmt = select(TaskModel).where(*conditions).order_by(TaskModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_assignee(
        self, assignee_username: str, chat_id: int | None = None
    ) -> list[TaskModel]:
        """Retrieves tasks assigned to target username."""
        clean_name = assignee_username.lstrip("@").lower()
        conditions = [
            TaskModel.assignee_username.ilike(f"%{clean_name}%"),
            TaskModel.deleted_at.is_(None),
        ]
        if chat_id is not None:
            conditions.append(TaskModel.telegram_chat_id == chat_id)

        stmt = select(TaskModel).where(*conditions).order_by(TaskModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(
        self, status: str, chat_id: int | None = None
    ) -> list[TaskModel]:
        """Retrieves tasks matching target status."""
        conditions = [
            TaskModel.status == status.upper(),
            TaskModel.deleted_at.is_(None),
        ]
        if chat_id is not None:
            conditions.append(TaskModel.telegram_chat_id == chat_id)

        stmt = select(TaskModel).where(*conditions).order_by(TaskModel.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_prefix(
        self, prefix: str, chat_id: int | None = None
    ) -> TaskModel | None:
        """Retrieves task matching short UUID prefix (e.g. 8-char hex)."""
        clean_prefix = prefix.strip().lower()
        tasks = await self.list_all_tasks(chat_id=chat_id)
        for t in tasks:
            if str(t.id).lower().startswith(clean_prefix):
                return t
        return None

    async def update_status(
        self, task_id: str, new_status: str, chat_id: int | None = None
    ) -> TaskModel | None:
        """Updates task status by task UUID or short prefix."""
        task = await self.get_by_id_prefix(task_id, chat_id=chat_id)
        if not task:
            try:
                uuid_obj = UUID(task_id)
                task = await self.get_by_id(uuid_obj)
                if task and chat_id is not None and task.telegram_chat_id != chat_id:
                    return None
            except ValueError:
                return None

        if task:
            task.status = new_status.upper()
            await self.session.flush()
        return task
