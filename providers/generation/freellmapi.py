"""FreeLLMAPI local gateway adapter (OpenAI-compatible)."""
from __future__ import annotations

from typing import Any

from providers.base import GenerationRequest
from providers.generation.openai_compatible import OpenAICompatibleAdapter


class FreeLLMAPIAdapter(OpenAICompatibleAdapter):
    """Adapter for a local FreeLLMAPI gateway exposing an OpenAI-compatible API."""

    provider_label = "FreeLLMAPI"
    default_base_url = "http://127.0.0.1:3001/v1"
    key_env_var = "FREELLMAPI_API_KEY"
    base_url_env_var = "FREELLMAPI_BASE_URL"
    default_model = "auto"

    def build_body(self, request: GenerationRequest) -> dict[str, Any]:
        body = super().build_body(request)
        if request.context_notes:
            body["messages"].append(
                {
                    "role": "assistant",
                    "content": f"[Context from previous sections]\n{request.context_notes}",
                }
            )
        return body
