"""OpenRouter adapter — the shared OpenAI-compatible transport with OpenRouter's endpoints."""
from __future__ import annotations

from backend.providers.adapters.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        super().__init__(provider_id="openrouter", api_key=api_key, model=model, base_url=base_url)
