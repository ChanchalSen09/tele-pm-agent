"""Assignee Resolution and Member Verification Helper."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.database.models.models import UserModel


def resolve_and_validate_assignee(
    assignee_input: str | None, group_users: list["UserModel"]
) -> tuple[str | None, bool]:
    """Resolves an assignee input string against registered group members.

    Returns:
        (resolved_username_or_display, is_valid)
        - If assignee_input is empty/None: returns (None, True) -> unassigned task.
        - If matched in group_users: returns (username or first_name, True).
        - If not matched in group_users: returns (None, False).
    """
    if not assignee_input:
        return (None, True)

    clean_input = assignee_input.lstrip("@").strip().lower()
    if not clean_input:
        return (None, True)

    if not group_users:
        # If no registered members recorded in DB yet, accept specified handle
        return (assignee_input.lstrip("@"), True)

    # 1. Exact match on username, first_name, last_name, or full name
    for user in group_users:
        uname = (user.username or "").lower()
        fname = (user.first_name or "").lower()
        lname = (user.last_name or "").lower()
        fullname = f"{fname} {lname}".strip().lower()

        if clean_input in (uname, fname, lname, fullname):
            resolved_name = user.username or user.first_name
            return (resolved_name, True)

    # 2. Substring match (e.g. "Sakib" matching "Sakib Ali" or "sakib_ali")
    for user in group_users:
        uname = (user.username or "").lower()
        fname = (user.first_name or "").lower()
        lname = (user.last_name or "").lower()
        fullname = f"{fname} {lname}".strip().lower()

        if (
            (clean_input and clean_input in uname)
            or (clean_input and clean_input in fname)
            or (clean_input and clean_input in lname)
            or (clean_input and clean_input in fullname)
        ):
            resolved_name = user.username or user.first_name
            return (resolved_name, True)

    # No match found among registered group members
    return (None, False)


def format_group_members_summary(group_users: list["UserModel"]) -> str:
    """Formats human-readable summary list of registered group members."""
    if not group_users:
        return "No members registered yet."

    members_strs: list[str] = []
    for user in group_users:
        display = user.first_name
        if user.last_name:
            display += f" {user.last_name}"
        if user.username:
            display += f" (@{user.username})"
        members_strs.append(display)

    return ", ".join(members_strs)
