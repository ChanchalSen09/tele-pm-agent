"""Unit tests for Gemini API Infrastructure Client Adapter."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import LLMException
from app.domain.interfaces.llm import LLMMessage
from app.infrastructure.llm.gemini_client import GeminiClientAdapter, get_gemini_client


@pytest.fixture
def mock_sdk_client() -> MagicMock:
    """Fixture returning a mock Google GenAI SDK Client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello! How can I help you today?"
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 12
    mock_response.usage_metadata.total_token_count = 22
    mock_response.candidates = [MagicMock(finish_reason="STOP")]

    mock_client.models.generate_content.return_value = mock_response
    return mock_client


@pytest.mark.asyncio
async def test_gemini_client_completion_success(mock_sdk_client: MagicMock) -> None:
    """Verifies completion generation returns populated LLMResponse domain object."""
    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=2,
    )
    adapter.client = mock_sdk_client

    history = [LLMMessage(role="user", content="Hi")]
    response = await adapter.generate_completion(
        system_prompt="You are a helpful assistant.",
        history=history,
        user_prompt="Hello",
    )

    assert response.generated_text == "Hello! How can I help you today?"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 12
    assert response.total_tokens == 22
    assert response.finish_reason == "STOP"
    assert response.model_name == "test_model"


@pytest.mark.asyncio
async def test_gemini_client_empty_response_raises_validation_error(
    mock_sdk_client: MagicMock,
) -> None:
    """Verifies empty output text raises validation exception."""
    mock_sdk_client.models.generate_content.return_value.text = ""
    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=1,
    )
    adapter.client = mock_sdk_client

    with pytest.raises(LLMException):
        await adapter.generate_completion(
            system_prompt="System",
            history=[],
            user_prompt="User",
        )


@pytest.mark.asyncio
async def test_gemini_client_retry_on_failure(mock_sdk_client: MagicMock) -> None:
    """Verifies client retries on transient exceptions up to max_retries."""
    mock_sdk_client.models.generate_content.side_effect = [
        Exception("API Error 1"),
        mock_sdk_client.models.generate_content.return_value,
    ]

    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=2,
    )
    adapter.client = mock_sdk_client

    response = await adapter.generate_completion(
        system_prompt="System",
        history=[],
        user_prompt="User",
    )

    assert response.generated_text == "Hello! How can I help you today?"
    assert mock_sdk_client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_gemini_client_structured_output(mock_sdk_client: MagicMock) -> None:
    """Verifies structured JSON output generation and parsing."""
    mock_sdk_client.models.generate_content.return_value.text = (
        '{"name": "Alice", "age": 30}'
    )
    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=1,
    )
    adapter.client = mock_sdk_client

    result = await adapter.generate_structured_output(
        system_prompt="System",
        user_prompt="Extract info",
        response_schema={},
    )

    assert result == {"name": "Alice", "age": 30}


@pytest.mark.asyncio
async def test_gemini_client_check_health_success(mock_sdk_client: MagicMock) -> None:
    """Verifies check_health returns True when API probe succeeds."""
    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=1,
    )
    adapter.client = mock_sdk_client

    is_healthy = await adapter.check_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_gemini_client_check_health_failure(mock_sdk_client: MagicMock) -> None:
    """Verifies check_health returns False when API probe fails."""
    mock_sdk_client.models.generate_content.side_effect = Exception("Auth Failure")
    adapter = GeminiClientAdapter(
        api_key="test_key",
        model_name="test_model",
        timeout_seconds=5.0,
        max_retries=1,
    )
    adapter.client = mock_sdk_client

    is_healthy = await adapter.check_health()
    assert is_healthy is False


def test_get_gemini_client_di_provider() -> None:
    """Verifies get_gemini_client DI provider returns adapter instance."""
    client = get_gemini_client()
    assert isinstance(client, GeminiClientAdapter)
