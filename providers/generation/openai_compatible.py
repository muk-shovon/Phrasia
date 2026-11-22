"""Shared adapter for OpenAI-compatible chat-completions APIs.

Groq, OpenAI, FreeLLMAPI, OpenRouter and user-defined endpoints all speak the
same ``/chat/completions`` dialect, so the request/response handling lives here
and the concrete adapters only declare their identity and defaults.
"""
from __future__ import annotations

import os
from typing import Any

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


class OpenAICompatibleAdapter(GenerationProvider):
    """Base class for providers exposing an OpenAI-compatible API."""

    provider_label = "Provider"
    default_base_url = ""
    key_env_var = ""
    base_url_env_var = ""
    default_model = ""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = credentials.resolve_secret(config.provider_id, self.key_env_var)
        saved_base = credentials.resolve_setting(config.provider_id, "base_url")
        self.base_url = (
            saved_base
            or (os.environ.get(self.base_url_env_var, "") if self.base_url_env_var else "")
            or config.base_url
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

    # ── Hooks for subclasses ──────────────────────────────────────────────────
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def build_body(self, request: GenerationRequest) -> dict[str, Any]:
        return {
            "model": request.model or self.model,
            "messages": [
                {"role": "system", "content": request.system_instruction},
                {"role": "user", "content": f"{request.user_instruction}\n\n{request.chunk_text}"},
            ],
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "stream": False,
        }

    # ── Generation ────────────────────────────────────────────────────────────
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=request.timeout_seconds) as client:
                resp = await client.post(url, headers=self.headers(), json=self.build_body(request))
                if not 200 <= resp.status_code < 300:
                    raise normalize_http_error(
                        resp.status_code,
                        resp.text or "",
                        provider_request_id=resp.headers.get("x-request-id"),
                    )
                data = resp.json()
                choices = data.get("choices", [])
                message = choices[0].get("message", {}) if choices else {}
                usage = data.get("usage", {})
                return GenerationResult(
                    output_text=(message.get("content") or "").strip(),
                    provider_id=self.provider_id,
                    model_id=data.get("model", request.model or self.model),
                    provider_request_id=resp.headers.get("x-routed-via")
                    or resp.headers.get("x-request-id"),
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    finish_reason=choices[0].get("finish_reason") if choices else None,
                )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                category=ProviderErrorCategory.TRANSIENT_PROVIDER_ERROR,
                message=f"{self.provider_label} request failed: {exc}",
                retryable=True,
            ) from exc

    async def health_check(self) -> ProviderHealth:
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(url, headers=self.headers())
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
