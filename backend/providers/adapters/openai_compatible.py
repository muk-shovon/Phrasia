"""Shared OpenAI-compatible /chat/completions base (Groq, OpenRouter, custom)."""
from __future__ import annotations

from backend.providers.base import (
    GenerationRequest,
    GenerationResult,
    Provider,
    ProviderFailure,
    get_json,
    post_json,
)


class OpenAICompatibleProvider(Provider):
    """Speaks the /chat/completions protocol used by Groq, OpenRouter and custom endpoints."""

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

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(self, request: GenerationRequest) -> GenerationResult:
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
        data = await post_json(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            payload=payload,
            timeout=request.timeout,
        )

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderFailure(
                "The provider returned no choices.", code="empty_response"
            )
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message", {})
        text = str(message.get("content", "")).strip() if isinstance(message, dict) else ""
        if not text:
            raise ProviderFailure(
                "The provider returned an empty response.", code="empty_response"
            )

        raw_finish = str(choice.get("finish_reason", "stop")).lower()
        finish = (
            "length"
            if raw_finish in {"length", "max_tokens", "max-tokens", "end_turn: max_tokens"}
            else "blocked" if raw_finish in {"content_filter"} else "stop"
        )
        model_id = str(data.get("model") or self.model)
        return GenerationResult(
            text=text,
            provider_id=self.provider_id,
            model_id=model_id,
            finish_reason=finish,
        )

    async def health(self) -> tuple[bool, str]:
        if self.provider_id != "custom" and not self.api_key:
            return False, "No API key configured."
        try:
            status, _ = await get_json(
                f"{self.base_url}/models", headers=self._headers()
            )
        except ProviderFailure as exc:
            return False, exc.message
        if status == 200:
            return True, "Reachable."
        if status in {401, 403}:
            return False, "The API key was rejected."
        if status == 404:
            return False, "The endpoint has no /models route; a key may still work."
        return False, f"Provider returned HTTP {status}."
