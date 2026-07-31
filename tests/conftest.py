"""Pytest Shared Fixtures and Mocks."""

import asyncio
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.interfaces.llm import ILLMProvider, LLMMessage, LLMResponse
from app.infrastructure.database.base import Base


class MockGeminiProvider(ILLMProvider):
    """Fake Gemini LLM Provider for Unit Testing."""

    async def generate_completion(
        self,
        system_prompt: str,
        history: list[LLMMessage],
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        return LLMResponse(
            generated_text="Mocked AI response for testing.",
            prompt_tokens=10,
            completion_tokens=15,
            total_tokens=25,
            latency_ms=100,
            finish_reason="STOP",
            model_name="mock-gemini-model",
        )

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return {"status": "mock_structured_output"}

    async def check_health(self) -> bool:
        return True


@pytest.fixture
def mock_llm_provider() -> ILLMProvider:
    """Fixture returning a mock LLM provider instance."""
    return MockGeminiProvider()


@pytest.fixture
async def db_session() -> AsyncSession:  # type: ignore[misc]
    """Fixture providing an in-memory SQLite AsyncSession for isolated tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def session_factory():
    """Fixture providing an in-memory SQLite SessionFactory for UnitOfWork tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    yield factory
    asyncio.run(engine.dispose())
