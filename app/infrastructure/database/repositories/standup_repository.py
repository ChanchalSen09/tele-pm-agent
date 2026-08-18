"""SQLAlchemy Async Standup Repository Implementation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.models import StandupLogModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class StandupRepository(SQLAlchemyBaseRepository[StandupLogModel]):
    """Repository managing StandupLogModel entities for proactive standups & check-ins."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=StandupLogModel)

    async def get_pending_checkin(
        self, telegram_user_id: int, telegram_chat_id: int | None = None
    ) -> StandupLogModel | None:
        """Retrieves active pending standup log for a given user."""
        stmt = select(StandupLogModel).where(
            StandupLogModel.telegram_user_id == telegram_user_id,
            StandupLogModel.status == "PENDING",
            StandupLogModel.deleted_at.is_(None),
        )
        if telegram_chat_id is not None:
            stmt = stmt.where(StandupLogModel.telegram_chat_id == telegram_chat_id)

        stmt = stmt.order_by(StandupLogModel.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def log_checkin(
        self,
        telegram_chat_id: int,
        telegram_user_id: int | None,
        checkin_type: str,
        prompt_text: str,
        task_id: uuid.UUID | None = None,
    ) -> StandupLogModel:
        """Creates a new standup check-in log entry."""
        log_entry = StandupLogModel(
            telegram_chat_id=telegram_chat_id,
            telegram_user_id=telegram_user_id,
            checkin_type=checkin_type,
            prompt_text=prompt_text,
            task_id=task_id,
            status="PENDING",
        )
        return await self.save(log_entry)

    async def mark_responded(
        self, log_id: uuid.UUID, response_text: str
    ) -> StandupLogModel | None:
        """Marks pending standup check-in as responded."""
        log_entry = await self.get_by_id(log_id)
        if log_entry:
            log_entry.user_response = response_text
            log_entry.status = "RESPONDED"
            await self.session.flush()
        return log_entry
