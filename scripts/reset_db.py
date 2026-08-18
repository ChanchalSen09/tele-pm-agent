"""Database Reset & Re-initialization Utility.

Safely drops all legacy/corrupted database tables and recreates a 100% fresh, clean database schema using SQLAlchemy ORM and Alembic migrations.
"""

import asyncio

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.infrastructure.database.base import Base

logger = structlog.get_logger(__name__)


async def reset_database() -> None:
    """Drops all existing database tables and recreates clean schema."""
    db_url = settings.DATABASE_URL
    print(f"🔄 Connecting to Database at: {db_url.split('@')[-1]}")

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        print("🗑️ Dropping all existing tables...")
        # Drop all tables with CASCADE in PostgreSQL
        await conn.execute(text("DROP TABLE IF EXISTS standup_logs CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS tasks CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS ai_responses CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS messages CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS conversations CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS organizations CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))

        await conn.run_sync(Base.metadata.drop_all)
        print("✨ Re-creating fresh database tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Database successfully wiped and reset to a clean state!")


if __name__ == "__main__":
    asyncio.run(reset_database())
