"""Groq adapter — the shared OpenAI-compatible transport with Groq's endpoints."""
from __future__ import annotations

from backend.providers.adapters.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        super().__init__(provider_id="groq", api_key=api_key, model=model, base_url=base_url)
