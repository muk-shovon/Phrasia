"""Generic adapter for user-defined OpenAI-compatible endpoints.

The base URL, model and (optionally) API key are supplied from Settings, which
makes local servers (Ollama, LM Studio, vLLM, LiteLLM) and self-hosted gateways
usable without touching environment files.
"""
from __future__ import annotations

from providers.base import ProviderConfig, ProviderHealth
from providers.generation.openai_compatible import OpenAICompatibleAdapter


class CustomAdapter(OpenAICompatibleAdapter):
    provider_label = "Custom endpoint"
    default_base_url = ""
    key_env_var = "CUSTOM_API_KEY"
    base_url_env_var = "CUSTOM_BASE_URL"
    default_model = ""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.provider_label = config.display_name or "Custom endpoint"

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    async def health_check(self) -> ProviderHealth:
        if not self.base_url:
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                message="No base URL configured",
            )
        return await super().health_check()
