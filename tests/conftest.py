"""Pytest Shared Fixtures and Mocks."""

from typing import Any

import pytest

from app.domain.interfaces.llm import ILLMProvider, LLMMessage, LLMResponse


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
