"""Unit tests for Telegram Routers, Handlers, and Middlewares."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message, User

from app.core.exceptions import DomainException
from app.presentation.telegram.middleware.context import RequestContextMiddleware
from app.presentation.telegram.middleware.errors import ExceptionHandlingMiddleware
from app.presentation.telegram.routers.health import handle_health
from app.presentation.telegram.routers.start import handle_help, handle_start


@pytest.mark.asyncio
async def test_start_command_handler() -> None:
    """Verifies /start command handler formats onboarding greeting."""
    message = AsyncMock(spec=Message)
    message.from_user = User(id=123, is_bot=False, first_name="Alice")
    message.answer = AsyncMock()

    await handle_start(message)

    message.answer.assert_called_once()
    _, kwargs = message.answer.call_args
    assert "Hello, *Alice*" in kwargs["text"]
    assert kwargs["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_help_command_handler() -> None:
    """Verifies /help command handler returns capabilities guide."""
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    await handle_help(message)

    message.answer.assert_called_once()
    _, kwargs = message.answer.call_args
    assert "Commands Directory" in kwargs["text"]


@pytest.mark.asyncio
async def test_health_command_handler() -> None:
    """Verifies /health command handler returns system diagnostic status."""
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    await handle_health(message)

    message.answer.assert_called_once()
    _, kwargs = message.answer.call_args
    assert "System Operational Status" in kwargs["text"]
    assert "Healthy" in kwargs["text"]


@pytest.mark.asyncio
async def test_request_context_middleware() -> None:
    """Verifies RequestContextMiddleware injects correlation_id."""
    middleware = RequestContextMiddleware()
    event = MagicMock()
    data: dict = {}

    async def dummy_handler(evt: MagicMock, d: dict) -> str:
        return d.get("correlation_id", "")

    cid = await middleware(dummy_handler, event, data)
    assert cid != ""
    assert len(cid) == 36  # Valid UUID string format


@pytest.mark.asyncio
async def test_exception_handling_middleware_domain_exception() -> None:
    """Verifies ExceptionHandlingMiddleware catches domain exceptions and sends user error."""
    middleware = ExceptionHandlingMiddleware()
    message = AsyncMock(spec=Message)
    message.answer = AsyncMock()

    async def failing_handler(evt: MagicMock, d: dict) -> None:
        raise DomainException("Test Domain Failure")

    await middleware(failing_handler, message, {})
    message.answer.assert_called_once()
    _, kwargs = message.answer.call_args
    assert "Test Domain Failure" in kwargs["text"]
