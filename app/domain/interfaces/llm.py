"""Domain Interface for Language Model Providers (ILLMProvider)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMMessage:
    """Domain representation of a chat history turn."""

    role: str  # 'user', 'assistant', or 'system'
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Domain representation of an LLM generation result."""

    generated_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    finish_reason: str
    model_name: str


class ILLMProvider(ABC):
    """Abstract interface contract for all LLM Provider adapters."""

    @abstractmethod
    async def generate_completion(
        self,
        system_prompt: str,
        history: list[LLMMessage],
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generates a text completion given system prompt, history, and user input."""
        pass

    @abstractmethod
    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generates a JSON completion adhering to a target schema."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Checks API provider reachability and key validity."""
        pass
