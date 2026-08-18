"""Intelligent Assignee Resolution Engine with Role Matching, Domain Expertise, OOO Warnings, & Fuzzy Typo Tolerance."""

import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.database.models.models import TaskModel, UserModel

OOO_KEYWORDS = {"vacation", "ooo", "out of office", "sick", "leave", "holiday", "away"}
ROLE_KEYWORDS = {
    "admin": ["admin", "owner", "lead"],
    "lead": ["admin", "lead", "owner"],
    "backend": ["backend", "api", "database", "server", "dev"],
    "frontend": ["frontend", "ui", "css", "web", "design"],
    "qa": ["qa", "tester", "test", "quality"],
}


def check_user_ooo_status(
    assignee_handle: str | None, tasks: list["TaskModel"] | None
) -> str | None:
    """Scans recent task progress notes to verify if target user logged an Out-Of-Office / Vacation status."""
    if not assignee_handle or not tasks:
        return None

    clean_handle = assignee_handle.lstrip("@").lower()
    for t in tasks:
        if t.assignee_username and t.assignee_username.lstrip("@").lower() == clean_handle:
            note = (t.progress_notes or "").lower()
            if any(k in note for k in OOO_KEYWORDS):
                return (
                    f"⚠️ Note: @{clean_handle} logged an Out-of-Office / Vacation update recently (\""
                    f"{t.progress_notes.strip()}\")."
                )
    return None


def resolve_domain_expert(
    keyword: str, tasks: list["TaskModel"], group_users: list["UserModel"]
) -> str | None:
    """Scans task history for keyword matches (e.g., 'auth', 'database') and returns top domain expert."""
    if not keyword or not tasks:
        return None

    clean_kw = keyword.lower().strip()
    expert_counts: dict[str, int] = {}

    for t in tasks:
        title = (t.title or "").lower()
        desc = (t.description or "").lower()
        if (clean_kw in title or clean_kw in desc) and t.assignee_username:
            user_handle = t.assignee_username.lstrip("@")
            expert_counts[user_handle] = expert_counts.get(user_handle, 0) + 1

    if expert_counts:
        top_expert = max(expert_counts.items(), key=lambda item: item[1])[0]
        return top_expert

    return None


def resolve_role_assignee(
    role_input: str, group_users: list["UserModel"]
) -> str | None:
    """Resolves role-based keywords ('admin', 'backend', 'qa', 'lead') against group member roles."""
    clean_role = role_input.lower().strip()
    if clean_role not in ROLE_KEYWORDS:
        return None

    target_tokens = ROLE_KEYWORDS[clean_role]
    for user in group_users:
        uname = (user.username or "").lower()
        fname = (user.first_name or "").lower()
        lname = (user.last_name or "").lower()
        full = f"{uname} {fname} {lname}"

        if any(tok in full for tok in target_tokens):
            return user.username or user.first_name

    return None


def resolve_and_validate_assignee(
    assignee_input: str | None,
    group_users: list["UserModel"],
    sender_user: "UserModel | None" = None,
    active_tasks: list["TaskModel"] | None = None,
) -> tuple[str | None, bool, str | None]:
    """Resolves an assignee input string using Fuzzy Matching, Role Resolution, Self-Assignment & Workload Balancing.

    Returns:
        (resolved_name, is_valid, ambiguity_message)
        - If unassigned: (None, True, None)
        - If unique match or fuzzy match: (username_or_display, True, None)
        - If ambiguous multiple matches: (None, False, ambiguity_prompt)
        - If fallback: (assignee_handle, True, None)
    """
    if not assignee_input:
        return (None, True, None)

    clean_input = assignee_input.lstrip("@").strip().lower()
    if not clean_input:
        return (None, True, None)

    # 1. Smart Self-Assignment ("me", "myself", "i'll do it")
    if clean_input in ("me", "myself", "my self", "i'll do it", "i will do it", "i will"):
        if sender_user:
            resolved_self = sender_user.username or sender_user.first_name
            return (resolved_self, True, None)

    # 2. Smart Workload Balancing ("auto", "least busy", "whoever is free", "anyone")
    if clean_input in ("auto", "least busy", "whoever is free", "anyone", "free dev", "available"):
        if group_users:
            task_counts: dict[str, int] = {
                (u.username or u.first_name): 0 for u in group_users
            }
            if active_tasks:
                for t in active_tasks:
                    if t.status in ("TODO", "IN_PROGRESS") and t.assignee_username:
                        handle = t.assignee_username.lstrip("@")
                        if handle in task_counts:
                            task_counts[handle] += 1

            least_busy_user = min(task_counts.items(), key=lambda item: item[1])[0]
            return (least_busy_user, True, None)

    # 3. Role-Based Resolution ("admin", "lead", "backend", "frontend", "qa")
    role_resolved = resolve_role_assignee(clean_input, group_users)
    if role_resolved:
        return (role_resolved, True, None)

    # 4. Domain Expertise Matching ("whoever built auth", "expert in database")
    expert_match = re.search(
        r"(?:whoever\s+built|expert\s+in|who\s+worked\s+on)\s+([a-zA-Z0-9_\s]+)",
        clean_input,
        re.IGNORECASE,
    )
    if expert_match and active_tasks:
        kw = expert_match.group(1).strip()
        expert_user = resolve_domain_expert(kw, active_tasks, group_users)
        if expert_user:
            return (expert_user, True, None)

    if not group_users:
        return (assignee_input.lstrip("@"), True, None)

    # 5. Exact and Substring Search for Group Members
    matches: list[UserModel] = []
    for user in group_users:
        uname = (user.username or "").lower()
        fname = (user.first_name or "").lower()
        lname = (user.last_name or "").lower()
        fullname = f"{fname} {lname}".strip().lower()

        if clean_input in (uname, fname, lname, fullname) or (
            clean_input and (clean_input == fname or clean_input == lname)
        ):
            matches.append(user)

    if not matches:
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
                matches.append(user)

    # 6. Fuzzy Matching with Typo Tolerance
    if not matches:
        fuzzy_scores: list[tuple[float, UserModel]] = []
        for user in group_users:
            uname = (user.username or "").lower()
            fname = (user.first_name or "").lower()
            lname = (user.last_name or "").lower()
            fullname = f"{fname} {lname}".strip().lower()

            score = max(
                SequenceMatcher(None, clean_input, uname).ratio(),
                SequenceMatcher(None, clean_input, fname).ratio(),
                SequenceMatcher(None, clean_input, lname).ratio(),
                SequenceMatcher(None, clean_input, fullname).ratio(),
            )
            if score >= 0.70:
                fuzzy_scores.append((score, user))

        if fuzzy_scores:
            fuzzy_scores.sort(key=lambda item: item[0], reverse=True)
            top_score = fuzzy_scores[0][0]
            top_matches = [user for score, user in fuzzy_scores if score == top_score]
            matches.extend(top_matches)

    # Deduplicate matches
    unique_matches = list(
        {(u.telegram_id, u.username, u.first_name): u for u in matches}.values()
    )

    if len(unique_matches) == 1:
        user = unique_matches[0]
        resolved_name = user.username or user.first_name
        return (resolved_name, True, None)

    if len(unique_matches) > 1:
        candidates_str_list = []
        for u in unique_matches:
            display = u.first_name
            if u.last_name:
                display += f" {u.last_name}"
            if u.username:
                display += f" (@{u.username})"
            candidates_str_list.append(display)

        candidates_fmt = ", ".join(candidates_str_list)
        ambiguity_msg = (
            f"🤔 *Which {assignee_input.capitalize()} did you mean?*\n\n"
            f"I found multiple group members matching *{assignee_input}*:\n"
            f"• {candidates_fmt}\n\n"
            f"Please specify their full name or @username so I can assign the task correctly!"
        )
        return (None, False, ambiguity_msg)

    return (assignee_input.lstrip("@"), True, None)


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
