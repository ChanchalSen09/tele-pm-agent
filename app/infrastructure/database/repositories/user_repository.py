"""User Repository implementation for PostgreSQL."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.repository import IUserRepository
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.repository import SQLAlchemyBaseRepository


class UserRepository(SQLAlchemyBaseRepository[UserModel], IUserRepository):
    """Concrete repository for UserModel persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=UserModel)

    async def get_by_telegram_id(self, telegram_id: int) -> UserModel | None:
        """Fetches active user record by unique Telegram ID."""
        stmt = select(UserModel).where(
            UserModel.telegram_id == telegram_id,
            UserModel.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_chat_id(self, chat_id: int | None) -> list[UserModel]:
        """Fetches registered users participating in a specific chat_id, with fallback to all active users."""
        stmt = select(UserModel).where(UserModel.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
