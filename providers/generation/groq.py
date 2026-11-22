"""Groq API generation adapter (OpenAI-compatible)."""
from __future__ import annotations

from providers.generation.openai_compatible import OpenAICompatibleAdapter


class GroqAdapter(OpenAICompatibleAdapter):
    """Adapter for the Groq API."""

    provider_label = "Groq"
    default_base_url = "https://api.groq.com/openai/v1"
    key_env_var = "GROQ_API_KEY"
    base_url_env_var = "GROQ_BASE_URL"
    default_model = "llama-3.3-70b-specdec"
