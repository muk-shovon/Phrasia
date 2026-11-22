"""Gemini API generation adapter."""
from __future__ import annotations

import os

import httpx

from phrasia_domain import ProviderErrorCategory
from providers import credentials
from providers.base import (
    GenerationProvider,
    GenerationRequest,
    GenerationResult,
    ProviderConfig,
    ProviderHealth,
)
from providers.errors import ProviderError, normalize_http_error


class GeminiAdapter(GenerationProvider):
    """Adapter for Google's native Gemini ``generateContent`` API."""

    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    default_model = "gemini-2.0-flash"

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = credentials.resolve_secret(config.provider_id, "GEMINI_API_KEY")
        self.base_url = (
            credentials.resolve_setting(config.provider_id, "base_url")
            or os.environ.get("GEMINI_BASE_URL", "")
            or self.default_base_url
        ).rstrip("/")
        self.model = (
            credentials.resolve_setting(config.provider_id, "model")
            or config.default_model
            or self.default_model
        )

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.model
        url = f"{self.base_url}/models/{model}:generateContent"
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{request.user_instruction}\n\n{request.chunk_text}"}
                    ],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": request.max_output_tokens,
                "temperature": request.temperature,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                resp = await client.post(url, headers=self._headers(), json=body)
                if not 200 <= resp.status_code < 300:
                    raise normalize_http_error(resp.status_code, resp.text or "")
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError(
                        category=ProviderErrorCategory.TRANSIENT_PROVIDER_ERROR,
                        message="Gemini returned no candidates",
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                output_text = " ".join(
                    part.get("text", "") for part in parts if "text" in part
                ).strip()
                usage = data.get("usageMetadata", {})
                return GenerationResult(
                    output_text=output_text,
                    provider_id=self.provider_id,
                    model_id=data.get("modelVersion", model),
                    input_tokens=usage.get("promptTokenCount"),
                    output_tokens=usage.get("candidatesTokenCount"),
                    finish_reason=candidates[0].get("finishReason"),
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                category=ProviderErrorCategory.TRANSIENT_PROVIDER_ERROR,
                message=f"Gemini request failed: {exc}",
                retryable=True,
            ) from exc

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
                healthy = 200 <= resp.status_code < 300
                return ProviderHealth(
                    provider_id=self.provider_id,
                    healthy=healthy,
                    status_code=resp.status_code,
                    message="healthy" if healthy else f"http {resp.status_code}",
                )
        except Exception as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                message=str(exc)[:200],
            )
