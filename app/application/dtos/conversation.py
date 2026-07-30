"""Data Transfer Objects (DTOs) for Conversation Workflows."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserMessageInputDTO:
    """DTO representing an incoming user conversational message payload."""

    user_id: str
    user_text: str
    correlation_id: str


@dataclass(frozen=True)
class ConversationResponseDTO:
    """DTO representing the generated output response payload for the user."""

    response_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    finish_reason: str
    model_name: str
    metadata: dict[str, str] = field(default_factory=dict)
