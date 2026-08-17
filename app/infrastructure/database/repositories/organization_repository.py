"""SQLAlchemy Async Organization Repository implementation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.models import OrganizationModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class OrganizationRepository(SQLAlchemyBaseRepository[OrganizationModel]):
    """Repository managing OrganizationModel entities for multi-tenant accounts."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=OrganizationModel)

    async def get_by_chat_id(self, telegram_chat_id: int) -> OrganizationModel | None:
        """Retrieves organization entity matching Telegram chat_id."""
        stmt = select(OrganizationModel).where(
            OrganizationModel.telegram_chat_id == telegram_chat_id,
            OrganizationModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self, telegram_chat_id: int, org_name: str = "Default Organization"
    ) -> OrganizationModel:
        """Resolves existing organization or provisions a new default tenant account."""
        org = await self.get_by_chat_id(telegram_chat_id)
        if not org:
            org = OrganizationModel(
                telegram_chat_id=telegram_chat_id,
                org_name=org_name,
                plan_tier="standard",
                monthly_token_limit=100000,
                tokens_consumed_this_month=0,
                is_active=True,
            )
            org = await self.save(org)
        return org

    async def increment_token_usage(self, telegram_chat_id: int, tokens: int) -> None:
        """Tracks LLM token consumption against organization monthly budget limit."""
        org = await self.get_by_chat_id(telegram_chat_id)
        if org:
            org.tokens_consumed_this_month += tokens
            await self.session.flush()
