"""Guardrails module for domain scope validation, prompt injection defense, and out-of-scope refusal generation."""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Standard friendly guardrail refusal message
PM_GUARDRAIL_REFUSAL_MESSAGE = (
    "🤖 *I am Kwartz, your AI Product Manager.*\n\n"
    "My role is strictly focused on managing project tasks, tracking team progress, "
    "pulling status updates, and coordinating sprint workflows.\n\n"
    "❌ *I cannot assist with general programming, writing code boilerplate, or off-topic queries.*\n\n"
    "💡 *Just chat with me in plain text:*\n"
    "• *'Create a task fix login API @alex'*\n"
    "• *'Show task board'*\n"
    "• *'Mark task 5d02ccee as DONE'*\n"
    "• *'Give me sprint status'*"
)

# Common prompt injection patterns trying to break PM persona
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"disregard\s+your\s+(system\s+)?prompt",
    r"you\s+are\s+now\s+a\w*",
    r"act\s+as\s+(standard\s+)?(chatgpt|dan|a\s+coding\s+assistant|a\s+python\s+compiler|a\s+cpp\s+compiler)",
    r"forget\s+your\s+rules",
    r"bypass\s+guardrails",
]

# Patterns representing out-of-scope generic code writing / non-PM technical requests
OUT_OF_SCOPE_PATTERNS = [
    r"write\s+.*(cpp|c\+\+|python|java|javascript|typescript|rust|golang|c#|sql|html|css).*(code|script|template|boiler|boilder|function|class|algorithm)",
    r"write\s+.*(code|script|template|boiler|boilder).*(cpp|c\+\+|python|java|javascript|typescript|rust|golang|c#|sql|html|css)",
    r"write\s+(a\s+)?(cpp|c\+\+|python|java|javascript|typescript|rust|go|c#|sql|html|css)",
    r"(cpp|c\+\+|python|java|javascript|typescript|rust|go|c#|sql|html|css)\s+(code|script|template|boiler|boilder)",
    r"write\s+code\s+for",
    r"code\s+(for\s+me|in\s+python|in\s+cpp|in\s+c\+\+|in\s+java)",
    r"generate\s+.*(code|script|program|template|boiler)",
    r"how\s+to\s+solve\s+leetcode",
    r"write\s+(a\s+)?(essay|poem|song|story)\s+about",
]


@dataclass(frozen=True)
class GuardrailResult:
    """Dataclass holding validation result for input text scope."""

    is_allowed: bool
    refusal_reason: str | None = None
    response_text: str | None = None


def validate_query_scope(user_text: str) -> GuardrailResult:
    """Evaluates input query against security injection patterns and PM domain scope limits."""
    if not user_text:
        return GuardrailResult(is_allowed=True)

    text_lower = user_text.lower().strip()

    # 1. Prompt Injection Defense
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower):
            logger.warning(
                "Prompt injection attempt detected and blocked by guardrail",
                pattern=pattern,
                query_snippet=text_lower[:50],
            )
            return GuardrailResult(
                is_allowed=False,
                refusal_reason="Prompt injection / persona override attempt blocked.",
                response_text=PM_GUARDRAIL_REFUSAL_MESSAGE,
            )

    # 2. Out-of-Scope Code Generation / Off-topic pattern check
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, text_lower):
            logger.info(
                "Off-topic / generic code request blocked by PM domain guardrail",
                pattern=pattern,
                query_snippet=text_lower[:50],
            )
            return GuardrailResult(
                is_allowed=False,
                refusal_reason="Out-of-scope generic code or non-PM query.",
                response_text=PM_GUARDRAIL_REFUSAL_MESSAGE,
            )

    return GuardrailResult(is_allowed=True)
