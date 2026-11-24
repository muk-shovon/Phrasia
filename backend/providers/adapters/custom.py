"""Custom OpenAI-compatible endpoint adapter. Base URL and model are user-supplied."""
from __future__ import annotations

from backend.providers.adapters.openai_compatible import OpenAICompatibleProvider


class CustomProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        super().__init__(provider_id="custom", api_key=api_key, model=model, base_url=base_url)
