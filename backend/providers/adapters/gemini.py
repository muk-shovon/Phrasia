"""Google Gemini generateContent adapter. Sends the system prompt via systemInstruction."""
from __future__ import annotations

from backend.providers.base import (
    GenerationRequest,
    GenerationResult,
    Provider,
    ProviderFailure,
    get_json,
    post_json,
)


class GeminiProvider(Provider):
    provider_id = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload: dict[str, object] = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [{"role": "user", "parts": [{"text": request.text}]}],
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
                "temperature": request.temperature,
            },
        }
        try:
            data = await post_json(
                url,
                headers=self._headers(),
                payload=payload,
                timeout=request.timeout,
            )
        except ProviderFailure:
            raise

        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderFailure(
                "Gemini returned no text. The prompt may have been blocked.",
                code="empty_response",
            )
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        content = candidate.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = "".join(
            str(part.get("text", "")) for part in parts if isinstance(part, dict)
        ).strip()
        if not text:
            raise ProviderFailure("Gemini returned an empty response.", code="empty_response")

        raw_finish = str(candidate.get("finishReason", "")).upper()
        if raw_finish in {"MAX_TOKENS", "LENGTH", "MAX_TOKENS_LIMIT", "TOKEN_LIMIT"}:
            finish = "length"
        elif raw_finish in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT"}:
            finish = "blocked"
        else:
            finish = "stop"

        return GenerationResult(
            text=text,
            provider_id=self.provider_id,
            model_id=self.model,
            finish_reason=finish,
        )

    async def health(self) -> tuple[bool, str]:
        if not self.api_key:
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
        return False, f"Provider returned HTTP {status}."
