"""Unit tests for Conversation Application Service."""

import pytest

from app.application.dtos.conversation import UserMessageInputDTO
from app.application.services.conversation_service import ConversationService
from app.core.exceptions import ValidationException
from app.domain.interfaces.llm import ILLMProvider


@pytest.mark.asyncio
async def test_process_user_message_success(mock_llm_provider: ILLMProvider) -> None:
    """Verifies standard user message processing flow and DTO result."""
    service = ConversationService(llm_provider=mock_llm_provider)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="What is clean architecture?",
        correlation_id="corr_456",
    )

    response = await service.process_user_message(input_dto)

    assert response.response_text == "Mocked AI response for testing."
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 15
    assert response.total_tokens == 25
    assert response.finish_reason == "STOP"
    assert service.get_user_context_length("user_123") == 2


@pytest.mark.asyncio
async def test_process_user_message_empty_text_raises_error(
    mock_llm_provider: ILLMProvider,
) -> None:
    """Verifies empty message raises ValidationException."""
    service = ConversationService(llm_provider=mock_llm_provider)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="   \x00   ",
        correlation_id="corr_456",
    )

    with pytest.raises(ValidationException, match="cannot be empty"):
        await service.process_user_message(input_dto)


@pytest.mark.asyncio
async def test_process_user_message_long_text_raises_error(
    mock_llm_provider: ILLMProvider,
) -> None:
    """Verifies long input text (> 4000 chars) raises ValidationException."""
    service = ConversationService(llm_provider=mock_llm_provider)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="a" * 4001,
        correlation_id="corr_456",
    )

    with pytest.raises(ValidationException, match="exceeds maximum length"):
        await service.process_user_message(input_dto)


@pytest.mark.asyncio
async def test_sliding_context_window_management(
    mock_llm_provider: ILLMProvider,
) -> None:
    """Verifies context history is trimmed to max_context_turns."""
    service = ConversationService(llm_provider=mock_llm_provider, max_context_turns=4)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="Hello",
        correlation_id="corr_1",
    )

    # Execute 3 turns (adds 6 messages total)
    await service.process_user_message(input_dto)
    await service.process_user_message(input_dto)
    await service.process_user_message(input_dto)

    # Truncation limits history window to last 4 turns
    assert service.get_user_context_length("user_123") == 4


@pytest.mark.asyncio
async def test_clear_user_context(mock_llm_provider: ILLMProvider) -> None:
    """Verifies clearing user context memory."""
    service = ConversationService(llm_provider=mock_llm_provider)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="Test prompt",
        correlation_id="corr_1",
    )

    await service.process_user_message(input_dto)
    assert service.get_user_context_length("user_123") == 2

    service.clear_user_context("user_123")
    assert service.get_user_context_length("user_123") == 0


@pytest.mark.asyncio
async def test_process_user_message_guardrail_refusal(
    mock_llm_provider: ILLMProvider,
) -> None:
    """Verifies out-of-scope query triggers immediate guardrail refusal without invoking LLM."""
    service = ConversationService(llm_provider=mock_llm_provider)
    input_dto = UserMessageInputDTO(
        user_id="user_123",
        user_text="write a cpp boilderlat code",
        correlation_id="corr_999",
    )

    response = await service.process_user_message(input_dto)

    assert response.finish_reason == "GUARDRAIL_REFUSAL"
    assert response.model_name == "guardrail_filter"
    assert "I am Kwartz, your AI Product Manager" in response.response_text
    assert "I cannot assist with general programming" in response.response_text

