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
from app.core.exceptions import (
    LLMException,
    RateLimitExceededException,
    ValidationException,
)
from app.domain.interfaces.llm import ILLMProvider, LLMMessage, LLMResponse

logger = structlog.get_logger(__name__)


class GeminiClientAdapter(ILLMProvider):
    """Google Gemini API Provider Adapter with multi-key failover, retries, timeouts, and health check support."""

    def __init__(
        self,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        if api_keys:
            self.api_keys = [k for k in api_keys if k and k.strip()]
        elif api_key:
            self.api_keys = [api_key]
        else:
            self.api_keys = settings.get_gemini_api_keys()

        self.model_name = model_name or settings.GEMINI_MODEL_NAME
        self.timeout_seconds = timeout_seconds or settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES

        raw_keys = self.api_keys or [""]
        self.clients = [genai.Client(api_key=key) for key in raw_keys]

    @property
    def client(self) -> genai.Client:
        """Property returning primary client for backward compatibility and test mock binding."""
        return self.clients[0] if self.clients else genai.Client(api_key="")

    @client.setter
    def client(self, value: genai.Client) -> None:
        """Property setter allowing test mocks to set primary client instance."""
        if self.clients:
            self.clients[0] = value
        else:
            self.clients = [value]

    async def generate_completion(
        self,
        system_prompt: str,
        history: list[LLMMessage],
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Executes text completion call against Gemini API with multi-key failover, retries, and timeouts."""
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

        candidate_models = [self.model_name]
        for fallback in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        attempt = 0
        last_exception: Exception | None = None

        for client_idx, active_client in enumerate(self.clients):
            for model_to_use in candidate_models:
                model_attempts = 0
                while model_attempts < self.max_retries:
                    try:
                        attempt += 1
                        model_attempts += 1
                        logger.debug(
                            "Dispatching Gemini API request",
                            attempt=attempt,
                            model=model_to_use,
                            key_index=client_idx,
                        )

                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                active_client.models.generate_content,
                                model=model_to_use,
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
                            model=model_to_use,
                            key_index=client_idx,
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
                            model_name=model_to_use,
                        )

                    except TimeoutError:
                        logger.warning(
                            "Gemini API call timed out",
                            attempt=attempt,
                            model=model_to_use,
                            key_index=client_idx,
                            timeout=self.timeout_seconds,
                        )
                        last_exception = LLMException("Gemini API request execution timed out.")
                    except Exception as e:
                        err_str = str(e)
                        is_rate_limit = (
                            "429" in err_str
                            or "RESOURCE_EXHAUSTED" in err_str
                            or "quota" in err_str.lower()
                        )
                        is_not_found = (
                            "404" in err_str
                            or "NOT_FOUND" in err_str
                            or "no longer available" in err_str.lower()
                        )
                        logger.warning(
                            "Gemini API execution attempt failed",
                            attempt=attempt,
                            model=model_to_use,
                            key_index=client_idx,
                            is_rate_limit=is_rate_limit,
                            error=err_str,
                        )
                        if is_rate_limit:
                            last_exception = RateLimitExceededException(retry_after=15 * attempt)
                        else:
                            last_exception = LLMException(f"Gemini API failure: {err_str}")

                        if is_not_found:
                            # Deprecated/invalid model endpoint - stop retrying this model and switch to next fallback
                            logger.warning(
                                "Model not found or deprecated, skipping remaining retries for this model",
                                model=model_to_use,
                            )
                            break

                        if (is_rate_limit or "503" in err_str) and len(self.clients) > 1 and client_idx < len(self.clients) - 1:
                            logger.warning(
                                "Rate limit or service overload on API key, failing over to next API key",
                                key_index=client_idx,
                            )
                            break

                        if model_attempts < self.max_retries:
                            base_delay = 5.0 if is_rate_limit else 1.0
                            jitter = random.uniform(0.8, 1.2)
                            backoff_delay = ((2 ** (model_attempts - 1)) * base_delay) * jitter
                            await asyncio.sleep(backoff_delay)

        raise last_exception or LLMException(
            "Gemini completion failed after max retries and failovers."
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

        last_exception: Exception | None = None

        for client_idx, active_client in enumerate(self.clients):
            attempt = 0
            while attempt < self.max_retries:
                try:
                    attempt += 1
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            active_client.models.generate_content,
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
                        key_index=client_idx,
                        error=str(exc),
                    )
                    last_exception = LLMException(f"Structured output error: {exc!s}")
                    if attempt < self.max_retries:
                        await asyncio.sleep(1.0)

        raise last_exception or LLMException(
            "Failed to generate structured JSON output."
        )

    async def check_health(self) -> bool:
        """Verifies Gemini API reachability across configured clients."""
        for active_client in self.clients:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        active_client.models.generate_content,
                        model=self.model_name,
                        contents="ping",
                        config=types.GenerateContentConfig(max_output_tokens=5),
                    ),
                    timeout=5.0,
                )
                return True
            except Exception as exc:
                logger.warning("Gemini Health Check Failed for API key client", error=str(exc))
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
        or _gemini_client_instance.api_keys != settings.get_gemini_api_keys()
    ):
        _gemini_client_instance = GeminiClientAdapter()
    return _gemini_client_instance
