"""Unit tests for TaskRepository and Task domain entity persistence."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.models import TaskModel
from app.infrastructure.database.repositories.task_repository import TaskRepository


@pytest.mark.asyncio
async def test_task_repository_crud(db_session: AsyncSession) -> None:
    """Verifies TaskRepository create, list, and status update operations."""
    repo = TaskRepository(db_session)

    # 1. Create Task
    task = TaskModel(
        title="Migrate database schema",
        description="Add tasks table to PostgreSQL",
        assignee_username="alex",
        status="TODO",
        created_by_telegram_id=123456,
    )
    saved_task = await repo.save(task)
    assert saved_task.id is not None
    assert saved_task.title == "Migrate database schema"

    # 2. Fetch all tasks
    all_tasks = await repo.list_all_tasks()
    assert len(all_tasks) == 1

    # 3. List by assignee
    alex_tasks = await repo.list_by_assignee("alex")
    assert len(alex_tasks) == 1
    assert alex_tasks[0].assignee_username == "alex"

    # 4. Update Status
    updated = await repo.update_status(str(saved_task.id), "IN_PROGRESS")
    assert updated is not None
    assert updated.status == "IN_PROGRESS"
