"""Prompt Builder, Dynamic Variable Substitution, and Token Optimization Engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from app.domain.interfaces.llm import LLMMessage
from app.infrastructure.llm.prompts.prompt_registry import (
    PromptRegistry,
    default_prompt_registry,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class PromptPayload:
    """Dataclass representing the fully assembled prompt payload ready for LLM generation."""

    system_prompt: str
    formatted_user_prompt: str
    history: list[LLMMessage]
    prompt_version: str
    estimated_tokens: int
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptBuilder:
    """Assembles prompt templates, dynamic variables, and optimizes token history limits."""

    def __init__(
        self,
        registry: PromptRegistry = default_prompt_registry,
        max_token_budget: int = 3000,
    ) -> None:
        self.registry = registry
        self.max_token_budget = max_token_budget

    def build_prompt_payload(
        self,
        user_text: str,
        history: list[LLMMessage] | None = None,
        prompt_name: str = "system_base",
        prompt_version: str | None = None,
        variables: dict[str, Any] | None = None,
    ) -> PromptPayload:
        """Assembles system prompt, structural tags, and optimizes context history token count."""
        template = self.registry.get(prompt_name, prompt_version)

        # Supply standard default dynamic variables if absent
        var_map = {
            "user_name": "User",
            "current_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "tier": "standard",
            "project_tasks": "No active database tasks.",
        }
        if variables:
            var_map.update(variables)

        rendered_system_prompt = template.render(var_map)
        formatted_user_prompt = f"<user_query>\n{user_text}\n</user_query>"

        # Token optimization: trim history window to stay within token budget
        raw_history = list(history) if history else []
        optimized_history = self._optimize_token_budget(
            system_prompt=rendered_system_prompt,
            user_prompt=formatted_user_prompt,
            history=raw_history,
        )

        total_estimated_tokens = (
            self._estimate_tokens(rendered_system_prompt)
            + self._estimate_tokens(formatted_user_prompt)
            + sum(self._estimate_tokens(msg.content) for msg in optimized_history)
        )

        logger.info(
            "Assembled Prompt Payload",
            prompt_name=prompt_name,
            version=template.version,
            history_turns=len(optimized_history),
            estimated_tokens=total_estimated_tokens,
        )

        return PromptPayload(
            system_prompt=rendered_system_prompt,
            formatted_user_prompt=formatted_user_prompt,
            history=optimized_history,
            prompt_version=f"{template.name}:{template.version}",
            estimated_tokens=total_estimated_tokens,
        )

    def _optimize_token_budget(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[LLMMessage],
    ) -> list[LLMMessage]:
        """Trims history window turns from oldest to newest if total tokens exceed token budget."""
        base_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(
            user_prompt
        )
        available_budget = self.max_token_budget - base_tokens

        if available_budget <= 0:
            logger.warning(
                "Base prompt consumes entire token budget; clearing history window."
            )
            return []

        trimmed_history = list(history)
        current_history_tokens = sum(
            self._estimate_tokens(msg.content) for msg in trimmed_history
        )

        while trimmed_history and current_history_tokens > available_budget:
            dropped_msg = trimmed_history.pop(0)
            current_history_tokens -= self._estimate_tokens(dropped_msg.content)
            logger.debug(
                "Trimmed old message turn for token optimization", role=dropped_msg.role
            )

        return trimmed_history

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimates token count for text payload (rough heuristic: ~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)
