"""Script to test PostgreSQL database connection and auto-create/sync ORM tables."""

import asyncio
import sys

import structlog
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.infrastructure.database.base import Base

logger = structlog.get_logger(__name__)


async def init_database(reset: bool = False) -> None:
    """Connects to configured PostgreSQL database and syncs schema tables."""
    print(f"Connecting to database: {settings.DATABASE_URL[:45]}...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            if reset:
                print("Resetting database schema (DROP ALL TABLES)...")
                await conn.run_sync(Base.metadata.drop_all)

            print("Creating database schema tables (CREATE TABLE IF NOT EXISTS)...")
            await conn.run_sync(Base.metadata.create_all)

        print("[SUCCESS] Database connection successful and tables synchronized!")
    except Exception as exc:
        print(f"[ERROR] Database initialization failed: {exc}", file=sys.stderr)
        raise exc
    finally:
        await engine.dispose()


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    asyncio.run(init_database(reset=reset_flag))
