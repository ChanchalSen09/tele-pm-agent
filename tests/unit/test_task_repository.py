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


@pytest.mark.asyncio
async def test_task_repository_group_chat_isolation(db_session: AsyncSession) -> None:
    """Verifies tasks created in Group A (chat_id=-1001) are isolated from Group B (chat_id=-1002)."""
    repo = TaskRepository(db_session)

    task_group_a = TaskModel(
        title="Group A Confidential Task",
        assignee_username="alice",
        status="TODO",
        created_by_telegram_id=100,
        telegram_chat_id=-1001,
    )
    task_group_b = TaskModel(
        title="Group B Secret Task",
        assignee_username="bob",
        status="TODO",
        created_by_telegram_id=200,
        telegram_chat_id=-1002,
    )

    await repo.save(task_group_a)
    await repo.save(task_group_b)

    # Group A should only see Group A task
    tasks_a = await repo.list_all_tasks(chat_id=-1001)
    assert len(tasks_a) == 1
    assert tasks_a[0].title == "Group A Confidential Task"

    # Group B should only see Group B task
    tasks_b = await repo.list_all_tasks(chat_id=-1002)
    assert len(tasks_b) == 1
    assert tasks_b[0].title == "Group B Secret Task"

    # Group B cannot update Group A task
    updated_cross = await repo.update_status(
        str(task_group_a.id), "DONE", chat_id=-1002
    )
    assert updated_cross is None

