"""OpenAI-compatible provider — works with any endpoint that speaks the OpenAI API.

Covers: OpenAI itself, xAI (Grok), OpenRouter, Together, Groq, DeepInfra, NVIDIA NIM,
plus any local OpenAI-compat server (Ollama's /v1, vLLM, llama-server, LM Studio).

Each model in models.yaml declares which API key env var and base URL to use:

    - name: gpt-5-mini
      provider: openai_compat
      api_id: gpt-5-mini
      api_key_env: OPENAI_API_KEY
      # base_url omitted → defaults to https://api.openai.com/v1

    - name: grok-3-mini
      provider: openai_compat
      api_id: grok-3-mini
      api_key_env: GROK_API_KEY
      base_url: https://api.x.ai/v1
"""

from __future__ import annotations

import asyncio
import os
import time

from openai import APIError, AsyncOpenAI, RateLimitError

from ..base import Completion, LLMProvider, Message, ModelMetadata, ProviderError, ToolSpec

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatProvider(LLMProvider):
    def __init__(self, meta: ModelMetadata):
        self._meta = meta
        env_var = meta.api_key_env or "OPENAI_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ProviderError(
                f"{env_var} is not set. Add it to .env before using {meta.name}."
            )
        # Resolution order for base_url: env-var indirection > literal > default OpenAI URL.
        base_url: str | None = None
        if meta.base_url_env:
            base_url = os.environ.get(meta.base_url_env)
            if not base_url:
                raise ProviderError(
                    f"{meta.base_url_env} is not set. Add it to .env before using {meta.name}."
                )
        else:
            base_url = meta.base_url or _DEFAULT_BASE_URL
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def metadata(self) -> ModelMetadata:
        return self._meta

    async def complete(
        self,
        system: str,
        messages: list[Message],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        tools: list[ToolSpec] | None = None,
        json_schema: dict | None = None,
    ) -> Completion:
        api_messages: list[dict] = [{"role": "system", "content": system}]
        api_messages.extend({"role": m.role, "content": m.content} for m in messages)

        last_err: Exception | None = None
        for attempt in range(3):
            t0 = time.monotonic()
            try:
                resp = await self._client.chat.completions.create(
                    model=self._meta.api_id,
                    messages=api_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                choice = resp.choices[0]
                text = choice.message.content or ""
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
                return Completion(
                    text=text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    model=self._meta.name,
                    provider=self._meta.provider,
                    latency_ms=latency_ms,
                )
            except RateLimitError as exc:
                last_err = exc
                await asyncio.sleep(2**attempt)
            except APIError as exc:
                last_err = exc
                if attempt == 2:
                    break
                await asyncio.sleep(2**attempt)

        raise ProviderError(
            f"OpenAI-compat call to {self._meta.name} failed after retries: {last_err!r}"
        )
