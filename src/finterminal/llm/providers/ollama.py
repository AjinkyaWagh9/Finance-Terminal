"""Ollama provider — Phase 2 implementation. Stub for Phase 1."""

from __future__ import annotations

from ..base import Completion, LLMProvider, Message, ModelMetadata, ProviderError, ToolSpec


class OllamaProvider(LLMProvider):
    def __init__(self, meta: ModelMetadata):
        self._meta = meta

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
        raise ProviderError(
            "OllamaProvider is a Phase 1 stub. "
            "Implement using ollama.AsyncClient in Phase 2 when you swap data/news agents to qwen3:8b."
        )
