"""Unit tests for Natural Language PM Action Execution Engine."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.natural_pm_engine import (
    parse_and_execute_natural_intent,
)
from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork


@pytest.mark.asyncio
async def test_natural_task_creation(db_session: AsyncSession) -> None:
    """Verifies plain text 'create task ...' intent creates task in DB."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        res = await parse_and_execute_natural_intent(
            user_text="Create a task to build auth service @alex",
            chat_id=-1001,
            creator_id=999,
            uow=uow,
        )

        assert res is not None
        assert res.action_type == "CREATE_TASK"
        assert "Build auth service" in res.response_text
        assert "@alex" in res.response_text

        # Verify task persisted in DB
        tasks = await uow.tasks.list_all_tasks(chat_id=-1001)
        assert len(tasks) == 1
        assert tasks[0].title == "Build auth service"
        assert tasks[0].assignee_username == "alex"


@pytest.mark.asyncio
async def test_natural_task_status_update(db_session: AsyncSession) -> None:
    """Verifies plain text 'mark task <id> as done' intent updates task status in DB."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        # Create initial task
        create_res = await parse_and_execute_natural_intent(
            user_text="Add task fix UI overflow @sam",
            chat_id=-1001,
            creator_id=888,
            uow=uow,
        )
        assert create_res is not None

        tasks = await uow.tasks.list_all_tasks(chat_id=-1001)
        task_prefix = str(tasks[0].id)[:8]

        # Natural status update
        update_res = await parse_and_execute_natural_intent(
            user_text=f"Mark task {task_prefix} as DONE",
            chat_id=-1001,
            creator_id=888,
            uow=uow,
        )
        assert update_res is not None
        assert update_res.action_type == "UPDATE_TASK"
        assert "Updated Task Status" in update_res.response_text

        # Verify status in DB
        tasks_updated = await uow.tasks.list_all_tasks(chat_id=-1001)
        assert tasks_updated[0].status == "DONE"


@pytest.mark.asyncio
async def test_natural_task_board_request(db_session: AsyncSession) -> None:
    """Verifies plain text 'show tasks' returns task board summary."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        res = await parse_and_execute_natural_intent(
            user_text="Show task board",
            chat_id=-1001,
            creator_id=777,
            uow=uow,
        )
        assert res is not None
        assert res.action_type == "LIST_TASKS"
        assert "Project Task Board" in res.response_text
