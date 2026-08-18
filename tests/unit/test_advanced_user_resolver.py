"""Unit tests for Advanced AI PM Assignee Suite (Roles, Domain Experts, OOO Warnings, Task Handoffs)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.natural_pm_engine import parse_and_execute_natural_intent
from app.application.services.user_resolver import (
    check_user_ooo_status,
    resolve_and_validate_assignee,
    resolve_domain_expert,
)
from app.infrastructure.database.models.models import TaskModel, UserModel
from app.infrastructure.database.repositories.unit_of_work import AsyncUnitOfWork


@pytest.fixture
def sample_users() -> list[UserModel]:
    return [
        UserModel(telegram_id=101, username="alex_lead", first_name="Alex", last_name="Lead"),
        UserModel(telegram_id=102, username="sarah_backend", first_name="Sarah", last_name="Backend"),
        UserModel(telegram_id=103, username="mike_qa", first_name="Mike", last_name="Tester"),
    ]


def test_role_based_assignee_resolution(sample_users: list[UserModel]) -> None:
    """Verifies role keywords like 'lead' or 'backend' resolve to appropriate team members."""
    name_lead, is_val, _ = resolve_and_validate_assignee("lead", sample_users)
    assert is_val is True
    assert name_lead == "alex_lead"

    name_qa, is_val, _ = resolve_and_validate_assignee("qa", sample_users)
    assert is_val is True
    assert name_qa == "mike_qa"


def test_domain_expert_matching(sample_users: list[UserModel]) -> None:
    """Verifies domain expert resolution scans past tasks for keyword matches."""
    past_tasks = [
        TaskModel(title="Build auth endpoints", assignee_username="sarah_backend", status="DONE", created_by_telegram_id=1),
        TaskModel(title="Refactor auth middleware", assignee_username="sarah_backend", status="DONE", created_by_telegram_id=1),
        TaskModel(title="Fix UI CSS", assignee_username="mike_qa", status="DONE", created_by_telegram_id=1),
    ]

    expert = resolve_domain_expert("auth", past_tasks, sample_users)
    assert expert == "sarah_backend"


def test_check_user_ooo_status(sample_users: list[UserModel]) -> None:
    """Verifies out-of-office / vacation detection scans progress notes."""
    tasks = [
        TaskModel(
            title="Update database",
            assignee_username="sarah_backend",
            progress_notes="On vacation until Monday",
            status="IN_PROGRESS",
            created_by_telegram_id=1,
        )
    ]

    warning = check_user_ooo_status("sarah_backend", tasks)
    assert warning is not None
    assert "Out-of-Office / Vacation" in warning
    assert "sarah_backend" in warning


@pytest.mark.asyncio
async def test_natural_task_reassignment(db_session: AsyncSession, sample_users: list[UserModel]) -> None:
    """Verifies natural task handoff ('transfer task <id> to Sarah') updates assignee in DB."""
    async with AsyncUnitOfWork(lambda: db_session) as uow:
        assert uow.tasks is not None
        task = TaskModel(
            title="Deploy auth server",
            assignee_username="mike_qa",
            status="IN_PROGRESS",
            created_by_telegram_id=101,
            telegram_chat_id=-1001,
        )
        saved_task = await uow.tasks.save(task)
        short_id = str(saved_task.id)[:8]

        res = await parse_and_execute_natural_intent(
            user_text=f"Transfer task {short_id} to Sarah",
            chat_id=-1001,
            creator_id=101,
            uow=uow,
            group_users=sample_users,
        )

        assert res is not None
        assert res.action_type == "REASSIGN_TASK"
        assert "Transferred" in res.response_text
        assert "sarah_backend" in res.response_text

        updated = await uow.tasks.get_by_id(saved_task.id)
        assert updated is not None
        assert updated.assignee_username == "sarah_backend"
