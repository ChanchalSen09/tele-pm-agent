"""FastAPI Webhook Server & Lifespan Entrypoint."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from aiogram.types import Update
from fastapi import FastAPI, Request, Response, status
from sqlalchemy import text

from app.application.services.reminder_service import check_and_send_due_task_reminders
from app.core.config import settings
from app.core.logger_setup import setup_logging
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import AsyncSessionFactory, engine
from app.presentation.telegram.bot import create_bot_and_dispatcher

# Configure structured logging on boot
setup_logging(log_level=settings.LOG_LEVEL)
logger = structlog.get_logger(__name__)

# Global instances
bot, dp = create_bot_and_dispatcher()


_background_tasks: set[asyncio.Task[Any]] = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application Lifespan Context Manager."""
    logger.info("Initializing Application Lifecycle...", env=settings.APP_ENV)

    # Auto-synchronize PostgreSQL tables and schema columns on boot
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            await conn.execute(
                text(
                    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT;"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_conversations_telegram_chat_id ON conversations (telegram_chat_id);"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT;"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_tasks_telegram_chat_id ON tasks (telegram_chat_id);"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITH TIME ZONE;"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'HIGH';"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'MEMBER';"
                )
            )
        logger.info("Database tables and schema auto-synchronized successfully.")
    except Exception as exc:
        logger.error("Failed to auto-sync database tables on startup", error=str(exc))

    # Launch periodic background due-date reminder task
    async def _reminder_loop() -> None:
        while True:
            await asyncio.sleep(1800)  # Check every 30 minutes
            await check_and_send_due_task_reminders(bot, AsyncSessionFactory)

    reminder_task = asyncio.create_task(_reminder_loop())
    _background_tasks.add(reminder_task)
    reminder_task.add_done_callback(_background_tasks.discard)

    if not settings.TELEGRAM_WEBHOOK_URL:
        logger.info("Starting Telegram Bot in Long Polling mode...")
        await bot.delete_webhook(drop_pending_updates=False)
        task = asyncio.create_task(dp.start_polling(bot))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    else:
        logger.info("Setting Telegram Webhook...", url=settings.TELEGRAM_WEBHOOK_URL)
        await bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET.get_secret_value() or None,
        )

    yield

    logger.info("Shutting down Application Lifecycle...")
    if not settings.TELEGRAM_WEBHOOK_URL:
        await dp.stop_polling()
    else:
        await bot.delete_webhook()

    await bot.session.close()
    logger.info("Application successfully shutdown.")


app = FastAPI(
    title="Telegram AI Bot API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """Health check endpoint for Docker & load balancer readiness probes."""
    db_healthy = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Health probe database ping failed", error=str(exc))
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "environment": settings.APP_ENV,
        "components": {
            "database": "up" if db_healthy else "down",
        },
    }


@app.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Ingress HTTP endpoint for Telegram Webhook updates."""
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET.get_secret_value()

    if expected_secret and secret_token != expected_secret:
        logger.warning("Unauthorized Webhook Access Attempt")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    update_data = await request.json()
    update = Update.model_validate(update_data, context={"bot": bot})

    await dp.feed_update(bot=bot, update=update)
    return Response(status_code=status.HTTP_200_OK)


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
