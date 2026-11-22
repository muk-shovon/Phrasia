"""Anthropic Messages API generation adapter."""
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


class AnthropicAdapter(GenerationProvider):
    """Adapter for Anthropic's native ``/v1/messages`` endpoint."""

    default_base_url = "https://api.anthropic.com/v1"
    default_model = "claude-3-5-haiku-20241022"

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = credentials.resolve_secret(config.provider_id, "ANTHROPIC_API_KEY")
        self.base_url = (
            credentials.resolve_setting(config.provider_id, "base_url")
            or os.environ.get("ANTHROPIC_BASE_URL", "")
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
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        body = {
            "model": request.model or self.model,
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "system": request.system_instruction,
            "messages": [
                {
                    "role": "user",
                    "content": f"{request.user_instruction}\n\n{request.chunk_text}",
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.base_url}/messages", headers=self._headers(), json=body
                )
                if not 200 <= resp.status_code < 300:
                    raise normalize_http_error(
                        resp.status_code,
                        resp.text or "",
                        provider_request_id=resp.headers.get("request-id"),
                    )
                data = resp.json()
                blocks = data.get("content", [])
                output_text = " ".join(
                    block.get("text", "")
                    for block in blocks
                    if block.get("type") == "text"
                ).strip()
                usage = data.get("usage", {})
                return GenerationResult(
                    output_text=output_text,
                    provider_id=self.provider_id,
                    model_id=data.get("model", request.model or self.model),
                    provider_request_id=resp.headers.get("request-id"),
                    input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"),
                    finish_reason=data.get("stop_reason"),
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                category=ProviderErrorCategory.TRANSIENT_PROVIDER_ERROR,
                message=f"Anthropic request failed: {exc}",
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
