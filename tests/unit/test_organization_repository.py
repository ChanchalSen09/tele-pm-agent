"""Unit tests for OrganizationRepository and Multi-Tenant Account Management."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)


@pytest.mark.asyncio
async def test_organization_repository_get_or_create(db_session: AsyncSession) -> None:
    """Verifies OrganizationRepository provisions default tenant accounts and tracks tokens."""
    repo = OrganizationRepository(db_session)

    org = await repo.get_or_create(telegram_chat_id=-1001, org_name="Acme Corp")
    assert org.id is not None
    assert org.telegram_chat_id == -1001
    assert org.org_name == "Acme Corp"
    assert org.monthly_token_limit == 100000

    # Idempotent get_or_create
    existing = await repo.get_or_create(telegram_chat_id=-1001)
    assert existing.id == org.id

    # Track token usage
    await repo.increment_token_usage(telegram_chat_id=-1001, tokens=500)
    fetched = await repo.get_by_chat_id(-1001)
    assert fetched is not None
    assert fetched.tokens_consumed_this_month == 500
