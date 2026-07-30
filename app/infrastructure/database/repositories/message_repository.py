"""Message Repository implementation for PostgreSQL."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.repository import IMessageRepository
from app.infrastructure.database.models import MessageModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class MessageRepository(SQLAlchemyBaseRepository[MessageModel], IMessageRepository):
    """Concrete repository for MessageModel persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=MessageModel)

    async def get_recent_by_conversation(
        self, conversation_id: UUID, limit: int = 10
    ) -> list[MessageModel]:
        """Fetches the most recent message turns for a conversation thread ordered sequentially."""
        stmt = (
            select(MessageModel)
            .where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.deleted_at.is_(None),
            )
            .order_by(MessageModel.sequence_number.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological sequence order
        return messages

    async def get_next_sequence_number(self, conversation_id: UUID) -> int:
        """Calculates next atomic sequence number for a message turn."""
        stmt = select(func.coalesce(func.max(MessageModel.sequence_number), 0)).where(
            MessageModel.conversation_id == conversation_id
        )
        result = await self.session.execute(stmt)
        current_max = result.scalar_one()
        return current_max + 1
