"""OpenRouter generation adapter (OpenAI-compatible aggregator)."""
from __future__ import annotations

import os

from providers.generation.openai_compatible import OpenAICompatibleAdapter


class OpenRouterAdapter(OpenAICompatibleAdapter):
    """Adapter for https://openrouter.ai — one key, many models.

    OpenRouter recommends ``HTTP-Referer`` and ``X-Title`` headers so traffic
    can be attributed to the app in their dashboard.
    """

    provider_label = "OpenRouter"
    default_base_url = "https://openrouter.ai/api/v1"
    key_env_var = "OPENROUTER_API_KEY"
    base_url_env_var = "OPENROUTER_BASE_URL"
    default_model = "openrouter/auto"

    def headers(self) -> dict[str, str]:
        headers = super().headers()
        headers["HTTP-Referer"] = os.environ.get("APP_BASE_URL", "http://localhost:3000")
        headers["X-Title"] = "Phrasia"
        return headers
