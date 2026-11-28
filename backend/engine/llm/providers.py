"""OpenAI-compatible and Gemini HTTP providers."""
from __future__ import annotations

import re
from typing import Any

from backend.engine.llm.base import LLMError, LLMProvider
from backend.engine.llm.transport import post_json

_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n?|\n?```\s*$")


def clean_output(text: str) -> str:
    value = (text or "").strip()
    if value.startswith("```") and value.endswith("```"):
        value = _FENCE.sub("", value).strip()
    return value


class OpenAICompatibleProvider(LLMProvider):
    """One class for every service that speaks the chat-completions schema."""

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.extra_headers = dict(extra_headers or {})

    def rewrite(
        self,
        system: str,
        user: str,
        params: dict[str, Any] | None = None,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 60,
        **_: Any,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if params:
            payload.update(params)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            **self.extra_headers,
        }
        data = post_json(
            f"{self.base_url}/chat/completions",
            payload,
            headers,
            timeout=timeout,
            provider=self.name,
        )
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError("Provider returned no choices.", retryable=True, provider=self.name)
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part)
                for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise LLMError("Provider returned an empty reply.", retryable=True, provider=self.name)
        return clean_output(content)


class GeminiProvider(LLMProvider):
    """Google AI Studio ``generateContent`` endpoint."""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self.name = "gemini"
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def rewrite(
        self,
        system: str,
        user: str,
        params: dict[str, Any] | None = None,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 60,
        **_: Any,
    ) -> str:
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if params:
            payload["generationConfig"].update(params)
        data = post_json(
            f"{self.base_url}/models/{self.model}:generateContent",
            payload,
            {"x-goog-api-key": self.api_key},
            timeout=timeout,
            provider=self.name,
        )
        feedback = data.get("promptFeedback")
        if isinstance(feedback, dict) and feedback.get("blockReason"):
            raise LLMError(
                f"Request blocked ({feedback.get('blockReason')}).",
                provider=self.name,
            )
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise LLMError("Gemini returned no candidates.", retryable=True, provider=self.name)
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise LLMError("Gemini returned an empty reply.", retryable=True, provider=self.name)
        text = "".join(
            str(part.get("text", "")) if isinstance(part, dict) else ""
            for part in parts
        )
        if not text.strip():
            reason = candidate.get("finishReason")
            raise LLMError(
                f"Gemini returned an empty reply{f' ({reason})' if reason else ''}.",
                retryable=True,
                provider=self.name,
            )
        return clean_output(text)
