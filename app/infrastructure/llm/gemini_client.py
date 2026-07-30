"""Google Gemini API Infrastructure Adapter implementation."""

import asyncio
import json
import random
import time
from typing import Any, cast

import structlog
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import LLMException, ValidationException
from app.domain.interfaces.llm import ILLMProvider, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)


class GeminiClientAdapter(ILLMProvider):
    """Google Gemini API Provider Adapter with retries, timeouts, and health check support."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY.get_secret_value()
        self.model_name = model_name or settings.GEMINI_MODEL_NAME
        self.timeout_seconds = timeout_seconds or settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES
        self.client = genai.Client(api_key=self.api_key)

    async def generate_completion(
        self,
        system_prompt: str,
        history: list[LLMMessage],
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Executes text completion call against Gemini API with retry and timeout controls."""
        start_time = time.perf_counter()

        contents: list[types.Content] = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
            )

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f"<user_query>\n{user_prompt}\n</user_query>"
                    )
                ],
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        attempt = 0
        last_exception: Exception | None = None

        while attempt < self.max_retries:
            try:
                attempt += 1
                logger.debug(
                    "Dispatching Gemini API request",
                    attempt=attempt,
                    model=self.model_name,
                )

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=self.timeout_seconds,
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)

                prompt_tokens = (
                    int(response.usage_metadata.prompt_token_count)
                    if response.usage_metadata
                    and response.usage_metadata.prompt_token_count is not None
                    else 0
                )
                completion_tokens = (
                    int(response.usage_metadata.candidates_token_count)
                    if response.usage_metadata
                    and response.usage_metadata.candidates_token_count is not None
                    else 0
                )
                total_tokens = (
                    int(response.usage_metadata.total_token_count)
                    if response.usage_metadata
                    and response.usage_metadata.total_token_count is not None
                    else 0
                )

                finish_reason = "STOP"
                if response.candidates and response.candidates[0].finish_reason:
                    finish_reason = str(response.candidates[0].finish_reason)

                generated_text = response.text or ""
                self._validate_response_text(generated_text)

                logger.info(
                    "Gemini Completion Generation Succeeded",
                    model=self.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                )

                return LLMResponse(
                    generated_text=generated_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    finish_reason=finish_reason,
                    model_name=self.model_name,
                )

            except TimeoutError:
                logger.warning(
                    "Gemini API call timed out",
                    attempt=attempt,
                    timeout=self.timeout_seconds,
                )
                last_exception = LLMException("Gemini API request execution timed out.")
            except Exception as e:
                logger.warning(
                    "Gemini API execution attempt failed", attempt=attempt, error=str(e)
                )
                last_exception = LLMException(f"Gemini API failure: {e!s}")

            if attempt < self.max_retries:
                jitter = random.uniform(0.8, 1.2)
                backoff_delay = ((2 ** (attempt - 1)) * 1.0) * jitter
                await asyncio.sleep(backoff_delay)

        raise last_exception or LLMException(
            "Gemini completion failed after max retries."
        )

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Executes Gemini API structured JSON generation adhering to target schema."""
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2,
        )

        attempt = 0
        last_exception: Exception | None = None

        while attempt < self.max_retries:
            try:
                attempt += 1
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=user_prompt,
                        config=config,
                    ),
                    timeout=self.timeout_seconds,
                )
                text_content = response.text or "{}"
                parsed_json = json.loads(text_content)
                return cast(dict[str, Any], parsed_json)
            except (TimeoutError, json.JSONDecodeError, Exception) as exc:
                logger.warning(
                    "Structured output generation attempt failed",
                    attempt=attempt,
                    error=str(exc),
                )
                last_exception = LLMException(f"Structured output error: {exc!s}")
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)

        raise last_exception or LLMException(
            "Failed to generate structured JSON output."
        )

    async def check_health(self) -> bool:
        """Verifies Gemini API reachability and client configuration."""
        try:
            # Perform lightweight dummy model probe
            await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents="ping",
                    config=types.GenerateContentConfig(max_output_tokens=5),
                ),
                timeout=5.0,
            )
            return True
        except Exception as exc:
            logger.warning("Gemini Health Check Failed", error=str(exc))
            return False

    def _validate_response_text(self, text: str) -> None:
        """Validates that output text is non-empty."""
        if not text or not text.strip():
            raise ValidationException("Gemini returned empty or invalid text content.")


# Dependency Injection Factory Provider
_gemini_client_instance: GeminiClientAdapter | None = None


def get_gemini_client() -> GeminiClientAdapter:
    """Dependency Injection provider returning GeminiClientAdapter instance."""
    global _gemini_client_instance  # noqa: PLW0603
    if (
        _gemini_client_instance is None
        or _gemini_client_instance.model_name != settings.GEMINI_MODEL_NAME
    ):
        _gemini_client_instance = GeminiClientAdapter()
    return _gemini_client_instance
