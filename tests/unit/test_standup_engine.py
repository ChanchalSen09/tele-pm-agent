"""Unit tests for StandupEngine (Group standups, midday check-in nudges, and reply processing)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.standup_engine import (
    process_standup_user_update,
    trigger_group_standup,
    trigger_midday_checkins,
)
from app.infrastructure.database.models.models import TaskModel
from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork


@pytest.mark.asyncio
async def test_trigger_group_standup(db_session: AsyncSession) -> None:
    """Verifies daily standup message formats assignees and active tasks."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title="Build login API",
            assignee_username="alex",
            status="IN_PROGRESS",
            created_by_telegram_id=123,
            telegram_chat_id=-1001,
        )
        await uow.tasks.save(task)

        standup_msg = await trigger_group_standup(chat_id=-1001, uow=uow)
        assert "Daily Standup Time!" in standup_msg
        assert "@ alex" in standup_msg or "@alex" in standup_msg
        assert "Build login API" in standup_msg


@pytest.mark.asyncio
async def test_trigger_midday_checkins(db_session: AsyncSession) -> None:
    """Verifies midday check-in nudges generate targeted messages for IN_PROGRESS and BLOCKED tasks."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title="Database migration",
            assignee_username="sarah",
            status="BLOCKED",
            created_by_telegram_id=123,
            telegram_chat_id=-1001,
        )
        await uow.tasks.save(task)

        nudges = await trigger_midday_checkins(chat_id=-1001, uow=uow)
        assert len(nudges) == 1
        assert "Mid-day Progress Check-in" in nudges[0]
        assert "@sarah" in nudges[0]
        assert "Database migration" in nudges[0]


@pytest.mark.asyncio
async def test_process_standup_user_update(db_session: AsyncSession) -> None:
    """Verifies user standup progress update updates task notes in DB."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title="Fix CSS styling",
            assignee_username="dev_john",
            status="IN_PROGRESS",
            created_by_telegram_id=456,
            telegram_chat_id=-1001,
        )
        await uow.tasks.save(task)

        reply = await process_standup_user_update(
            user_id=456,
            username="dev_john",
            user_text="Finished header layout, working on footer now",
            chat_id=-1001,
            uow=uow,
        )

        assert reply is not None
        assert "Status Update Logged!" in reply
        assert "Fix CSS styling" in reply
        assert "Finished header layout" in reply

        updated_task = await uow.tasks.get_by_id(task.id)
        assert updated_task is not None
        assert updated_task.progress_notes == "Finished header layout, working on footer now"
