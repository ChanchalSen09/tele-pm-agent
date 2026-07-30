"""Unit tests for Prompt Templates, Registry, and Prompt Builder Token Optimization."""

import pytest

from app.application.services.prompt_builder import PromptBuilder
from app.core.exceptions import ValidationException
from app.domain.interfaces.llm import LLMMessage
from app.infrastructure.llm.prompts.prompt_registry import (
    PromptRegistry,
    PromptTemplate,
)


def test_prompt_template_rendering() -> None:
    """Verifies template renders dynamic variables correctly."""
    template = PromptTemplate(
        name="custom_prompt",
        version="v1.0.0",
        template_text="Hello {user_name}, tier: {tier}",
    )
    rendered = template.render({"user_name": "Alice", "tier": "premium"})
    assert rendered == "Hello Alice, tier: premium"


def test_prompt_template_missing_variable_raises_error() -> None:
    """Verifies missing template variables trigger ValidationException."""
    template = PromptTemplate(
        name="custom_prompt",
        version="v1.0.0",
        template_text="Hello {user_name}, tier: {tier}",
    )
    with pytest.raises(ValidationException, match="Missing required prompt variable"):
        template.render({"user_name": "Alice"})


def test_prompt_registry_versioning() -> None:
    """Verifies prompt registry stores and retrieves versioned templates."""
    registry = PromptRegistry()
    v1 = PromptTemplate(
        name="test_prompt",
        version="v1.0.0",
        template_text="Version 1: {user_name}",
    )
    v2 = PromptTemplate(
        name="test_prompt",
        version="v2.0.0",
        template_text="Version 2: {user_name}",
    )

    registry.register(v1, set_active=True)
    registry.register(v2, set_active=False)

    assert registry.get("test_prompt").version == "v1.0.0"
    assert registry.get("test_prompt", "v2.0.0").version == "v2.0.0"

    registry.set_active_version("test_prompt", "v2.0.0")
    assert registry.get("test_prompt").version == "v2.0.0"


def test_prompt_builder_xml_tagging() -> None:
    """Verifies user prompt is encapsulated within structural <user_query> tags."""
    builder = PromptBuilder()
    payload = builder.build_prompt_payload(
        user_text="What is Python?",
        variables={
            "user_name": "Bob",
            "current_time": "2026-07-30 15:00 UTC",
            "tier": "standard",
        },
    )

    assert (
        "<user_query>\nWhat is Python?\n</user_query>" in payload.formatted_user_prompt
    )
    assert "User Name: Bob" in payload.system_prompt
    assert payload.prompt_version == "system_base:v1.0.0"
    assert payload.estimated_tokens > 0


def test_token_optimization_history_trimming() -> None:
    """Verifies history turns are trimmed from oldest to newest when token budget is exceeded."""
    builder = PromptBuilder(max_token_budget=100)  # Tight budget for testing

    long_history = [
        LLMMessage(role="user", content="A" * 200),  # ~50 tokens
        LLMMessage(role="assistant", content="B" * 200),  # ~50 tokens
        LLMMessage(role="user", content="C" * 40),  # ~10 tokens
    ]

    payload = builder.build_prompt_payload(
        user_text="Hi",
        history=long_history,
    )

    # Oldest long messages trimmed to stay under budget of 100
    assert len(payload.history) < len(long_history)
