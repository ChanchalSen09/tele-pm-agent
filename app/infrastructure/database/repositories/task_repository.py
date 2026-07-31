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

    async def get_by_title(self, title: str) -> TaskModel | None:
        """Retrieves task matching title."""
        stmt = select(TaskModel).where(
            TaskModel.title == title, TaskModel.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_tasks(self) -> list[TaskModel]:
        """Retrieves all active project tasks ordered by creation date."""
        stmt = (
            select(TaskModel)
            .where(TaskModel.deleted_at.is_(None))
            .order_by(TaskModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_assignee(self, assignee_username: str) -> list[TaskModel]:
        """Retrieves tasks assigned to target username."""
        clean_name = assignee_username.lstrip("@").lower()
        stmt = (
            select(TaskModel)
            .where(
                TaskModel.assignee_username.ilike(f"%{clean_name}%"),
                TaskModel.deleted_at.is_(None),
            )
            .order_by(TaskModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[TaskModel]:
        """Retrieves tasks matching target status."""
        stmt = (
            select(TaskModel)
            .where(
                TaskModel.status == status.upper(),
                TaskModel.deleted_at.is_(None),
            )
            .order_by(TaskModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, task_id: str, new_status: str) -> TaskModel | None:
        """Updates task status by task UUID."""
        try:
            uuid_obj = UUID(task_id)
        except ValueError:
            return None

        task = await self.get_by_id(uuid_obj)
        if task:
            task.status = new_status.upper()
            await self.session.flush()
        return task
