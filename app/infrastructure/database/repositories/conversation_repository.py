"""Conversation Repository implementation for PostgreSQL."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.repository import IConversationRepository
from app.infrastructure.database.models import ConversationModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class ConversationRepository(
    SQLAlchemyBaseRepository[ConversationModel], IConversationRepository
):
    """Concrete repository for ConversationModel persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=ConversationModel)

    async def get_active_by_user_id(self, user_id: UUID) -> ConversationModel | None:
        """Fetches active conversation thread for a specific user ID."""
        stmt = (
            select(ConversationModel)
            .where(
                ConversationModel.user_id == user_id,
                ConversationModel.is_active.is_(True),
                ConversationModel.deleted_at.is_(None),
            )
            .order_by(ConversationModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def archive_all_active_by_user_id(self, user_id: UUID) -> None:
        """Archives all active threads for a user (e.g. on /reset trigger)."""
        stmt = (
            update(ConversationModel)
            .where(
                ConversationModel.user_id == user_id,
                ConversationModel.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self.session.execute(stmt)
