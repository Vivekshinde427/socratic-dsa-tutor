import asyncio
import json
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel
from google import genai
from google.genai import types

from backend.app.config import settings
from backend.app.core.logging import logger

T = TypeVar("T", bound=BaseModel)


class LLMServiceError(Exception):
    """Base exception for LLM provider errors."""
    pass


class GeminiService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        max_retries: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.max_retries = max_retries or settings.GEMINI_MAX_RETRIES
        self.temperature = (
            temperature if temperature is not None else settings.GEMINI_TEMPERATURE
        )
        self._client: Optional[genai.Client] = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise LLMServiceError(
                    "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        config = types.GenerateContentConfig(
            temperature=temp,
            system_instruction=system_instruction,
        )

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                # Run synchronous client call in threadpool for async compatibility
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                latency_ms = (time.time() - start_time) * 1000

                usage_meta = getattr(response, "usage_metadata", None)
                prompt_tokens = getattr(usage_meta, "prompt_token_count", None)
                candidate_tokens = getattr(usage_meta, "candidates_token_count", None)
                total_tokens = getattr(usage_meta, "total_token_count", None)

                logger.info(
                    f"Gemini call succeeded | model={self.model_name} | "
                    f"attempt={attempt} | latency_ms={latency_ms:.1f} | "
                    f"tokens: prompt={prompt_tokens}, candidate={candidate_tokens}, total={total_tokens}"
                )
                return response.text or ""

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                last_error = e
                logger.warning(
                    f"Gemini call failed (attempt {attempt}/{self.max_retries}) | "
                    f"latency_ms={latency_ms:.1f} | error={str(e)}"
                )
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    await asyncio.sleep(backoff)

        raise LLMServiceError(
            f"Failed to generate text from Gemini after {self.max_retries} attempts: {last_error}"
        ) from last_error

    async def generate_structured(
        self,
        prompt: str,
        schema_class: Type[T],
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> T:
        temp = temperature if temperature is not None else self.temperature
        config = types.GenerateContentConfig(
            temperature=temp,
            system_instruction=system_instruction,
            response_mime_type="application/json",
        )

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
                latency_ms = (time.time() - start_time) * 1000

                raw_text = response.text or ""
                # Strip any accidental markdown formatting
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text.strip(), flags=re.MULTILINE)

                parsed_json = json.loads(cleaned_text)
                validated_model = schema_class.model_validate(parsed_json)

                usage_meta = getattr(response, "usage_metadata", None)
                total_tokens = getattr(usage_meta, "total_token_count", None)

                logger.info(
                    f"Gemini structured call succeeded | model={self.model_name} | "
                    f"latency_ms={latency_ms:.1f} | total_tokens={total_tokens}"
                )
                return validated_model

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                last_error = e
                logger.warning(
                    f"Gemini structured call failed (attempt {attempt}/{self.max_retries}) | "
                    f"latency_ms={latency_ms:.1f} | error={str(e)}"
                )
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    await asyncio.sleep(backoff)

        raise LLMServiceError(
            f"Failed structured generation after {self.max_retries} attempts: {last_error}"
        ) from last_error


# Default service singleton
gemini_service = GeminiService()
