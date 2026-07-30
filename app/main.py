"""FastAPI Webhook Server & Lifespan Entrypoint."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from aiogram.types import Update
from fastapi import FastAPI, Request, Response, status

from app.core.config import settings
from app.core.logger_setup import setup_logging
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
async def health_check() -> dict[str, str]:
    """Health check endpoint for Docker & load balancer readiness probes."""
    return {"status": "healthy", "environment": settings.APP_ENV}


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
