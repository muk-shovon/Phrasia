"""The one generic OpenAI-compatible adapter.

Used by every provider in the catalog. Anonymous lanes are enforced by the
per-provider ``RateLimiter`` in ``backend/providers/base.py``.
"""
from __future__ import annotations

from backend.providers.base import (
    GenerationRequest,
    GenerationResult,
    Provider,
    ProviderFailure,
    get_json,
    post_json,
    rate_limiter_for,
)


class OpenAICompatibleProvider(Provider):
    def __init__(
        self,
        provider_id: str,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self.provider_id = provider_id
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.limiter = rate_limiter_for(provider_id)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        await self.limiter.wait_if_limited(self.provider_id)
        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.text},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }
        try:
            data = await post_json(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                payload=payload,
                timeout=request.timeout,
            )
        except ProviderFailure as exc:
            if exc.code == "rate_limited" and exc.status == 429:
                retry_after = float(exc.status or 0)
                self.limiter.note_429(self.provider_id, retry_after or 30.0)
            raise

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderFailure("The provider returned no choices.", code="empty_response")
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message", {})
        text = str(message.get("content", "")).strip() if isinstance(message, dict) else ""
        if not text:
            raise ProviderFailure("The provider returned an empty response.", code="empty_response")

        raw_finish = str(choice.get("finish_reason", "stop")).lower()
        finish = "length" if raw_finish in {"length", "max_tokens", "content_filter"} else "stop"
        model_id = str(data.get("model") or self.model)
        return GenerationResult(
            text=text,
            provider_id=self.provider_id,
            model_id=model_id,
            finish_reason=finish,
        )

    async def health(self) -> tuple[bool, str]:
        try:
            status, _ = await get_json(
                f"{self.base_url}/models", headers=self._headers()
            )
        except ProviderFailure as exc:
            return False, exc.message
        if status == 200:
            return True, "Reachable."
        if status in {401, 403}:
            return False, "The endpoint rejected the key."
        return False, f"Provider returned HTTP {status}."
