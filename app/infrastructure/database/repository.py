"""Generic SQLAlchemy Base Repository Implementation."""

from datetime import datetime, timezone
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces.repository import IBaseRepository
from app.infrastructure.database.base import Base

T = TypeVar("T", bound=Base)


class SQLAlchemyBaseRepository(IBaseRepository[T], Generic[T]):
    """SQLAlchemy implementation of generic base repository."""

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, entity_id: UUID) -> T | None:
        """Fetch entity by ID filtering out soft-deleted records."""
        stmt = select(self.model_cls).where(
            self.model_cls.id == entity_id,
            self.model_cls.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, entity: T) -> T:
        """Persist or merge entity in current transaction session."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        """Perform soft deletion by setting deleted_at timestamp."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False
        entity.deleted_at = datetime.now(timezone.utc)
        await self.save(entity)
        return True
