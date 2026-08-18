"""Unit tests for intelligent user resolution, fuzzy typo tolerance, self-assignment, and ambiguity detection."""

import pytest

from app.application.services.user_resolver import (
    format_group_members_summary,
    resolve_and_validate_assignee,
)
from app.infrastructure.database.models.models import TaskModel, UserModel


@pytest.fixture
def sample_group_users() -> list[UserModel]:
    """Fixture providing sample group member entities."""
    return [
        UserModel(
            telegram_id=101,
            username="sakib_ali",
            first_name="Sakib",
            last_name="Ali",
        ),
        UserModel(
            telegram_id=102,
            username="rtk_admin",
            first_name="RTK",
            last_name=None,
        ),
        UserModel(
            telegram_id=103,
            username="aditya_m",
            first_name="Aditya",
            last_name="Mandleshwar",
        ),
        UserModel(
            telegram_id=104,
            username="aditya_s",
            first_name="Aditya",
            last_name="Sharma",
        ),
    ]


def test_resolve_valid_assignee_by_first_name(sample_group_users: list[UserModel]) -> None:
    """Verifies resolving assignee by first name 'Sakib' matches 'sakib_ali'."""
    name, is_valid, ambiguity = resolve_and_validate_assignee("Sakib", sample_group_users)
    assert is_valid is True
    assert name == "sakib_ali"
    assert ambiguity is None


def test_resolve_valid_assignee_by_handle(sample_group_users: list[UserModel]) -> None:
    """Verifies resolving assignee by handle '@sakib_ali'."""
    name, is_valid, ambiguity = resolve_and_validate_assignee("@sakib_ali", sample_group_users)
    assert is_valid is True
    assert name == "sakib_ali"
    assert ambiguity is None


def test_resolve_fuzzy_typo_matching(sample_group_users: list[UserModel]) -> None:
    """Verifies fuzzy matching resolves typos like 'Sakeeb' to 'sakib_ali'."""
    name, is_valid, ambiguity = resolve_and_validate_assignee("Sakeeb", sample_group_users)
    assert is_valid is True
    assert name == "sakib_ali"
    assert ambiguity is None


def test_resolve_self_assignment(sample_group_users: list[UserModel]) -> None:
    """Verifies assigning to 'me' or 'myself' resolves to the sender entity."""
    sender = sample_group_users[1]  # RTK
    name, is_valid, ambiguity = resolve_and_validate_assignee(
        "me", sample_group_users, sender_user=sender
    )
    assert is_valid is True
    assert name == "rtk_admin"
    assert ambiguity is None


def test_resolve_workload_balancing(sample_group_users: list[UserModel]) -> None:
    """Verifies assigning to 'auto' picks team member with lowest workload."""
    active_tasks = [
        TaskModel(assignee_username="sakib_ali", status="IN_PROGRESS", created_by_telegram_id=1, title="T1"),
        TaskModel(assignee_username="sakib_ali", status="TODO", created_by_telegram_id=1, title="T2"),
        TaskModel(assignee_username="rtk_admin", status="IN_PROGRESS", created_by_telegram_id=1, title="T3"),
    ]
    # aditya_m has 0 tasks -> should be picked
    name, is_valid, ambiguity = resolve_and_validate_assignee(
        "auto", sample_group_users, active_tasks=active_tasks
    )
    assert is_valid is True
    assert name in ("aditya_m", "aditya_s")
    assert ambiguity is None


def test_resolve_ambiguous_assignee_asks_clarification(sample_group_users: list[UserModel]) -> None:
    """Verifies assigning to 'Aditya' when 2 Adityas exist triggers ambiguity prompt."""
    name, is_valid, ambiguity = resolve_and_validate_assignee("Aditya", sample_group_users)
    assert is_valid is False
    assert name is None
    assert ambiguity is not None
    assert "Which Aditya did you mean?" in ambiguity
    assert "Aditya Mandleshwar" in ambiguity
    assert "Aditya Sharma" in ambiguity


def test_resolve_full_name_resolves_ambiguity(sample_group_users: list[UserModel]) -> None:
    """Verifies specifying full name 'Aditya Mandleshwar' uniquely resolves to 'aditya_m'."""
    name, is_valid, ambiguity = resolve_and_validate_assignee("Aditya Mandleshwar", sample_group_users)
    assert is_valid is True
    assert name == "aditya_m"
    assert ambiguity is None


def test_format_group_members_summary(sample_group_users: list[UserModel]) -> None:
    """Verifies formatting of group members summary string."""
    summary = format_group_members_summary(sample_group_users)
    assert "Sakib Ali (@sakib_ali)" in summary
    assert "RTK (@rtk_admin)" in summary
    assert "Aditya Mandleshwar (@aditya_m)" in summary
