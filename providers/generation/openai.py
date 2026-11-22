"""OpenAI generation adapter (OpenAI-compatible)."""
from __future__ import annotations

from providers.generation.openai_compatible import OpenAICompatibleAdapter


class OpenAIAdapter(OpenAICompatibleAdapter):
    """Adapter for the OpenAI API."""

    provider_label = "OpenAI"
    default_base_url = "https://api.openai.com/v1"
    key_env_var = "OPENAI_API_KEY"
    base_url_env_var = "OPENAI_BASE_URL"
    default_model = "gpt-4o-mini"
