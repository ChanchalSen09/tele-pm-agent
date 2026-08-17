"""Unit tests for user resolution and assignee validation against group members."""

import pytest

from app.application.services.user_resolver import (
    format_group_members_summary,
    resolve_and_validate_assignee,
)
from app.infrastructure.database.models.models import UserModel


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
            username="aakash_dev",
            first_name="Aakash",
            last_name="Kamavat",
        ),
    ]


def test_resolve_valid_assignee_by_first_name(sample_group_users: list[UserModel]) -> None:
    """Verifies resolving assignee by first name 'Sakib' matches 'sakib_ali'."""
    name, is_valid = resolve_and_validate_assignee("Sakib", sample_group_users)
    assert is_valid is True
    assert name == "sakib_ali"


def test_resolve_valid_assignee_by_handle(sample_group_users: list[UserModel]) -> None:
    """Verifies resolving assignee by handle '@sakib_ali'."""
    name, is_valid = resolve_and_validate_assignee("@sakib_ali", sample_group_users)
    assert is_valid is True
    assert name == "sakib_ali"


def test_resolve_invalid_assignee_returns_false(sample_group_users: list[UserModel]) -> None:
    """Verifies assigning to non-existent group member 'John' returns is_valid=False."""
    name, is_valid = resolve_and_validate_assignee("John", sample_group_users)
    assert is_valid is False
    assert name is None


def test_format_group_members_summary(sample_group_users: list[UserModel]) -> None:
    """Verifies formatting of group members summary string."""
    summary = format_group_members_summary(sample_group_users)
    assert "Sakib Ali (@sakib_ali)" in summary
    assert "RTK (@rtk_admin)" in summary
    assert "Aakash Kamavat (@aakash_dev)" in summary
