"""Provider chain with caching and automatic fallback."""
from __future__ import annotations

import hashlib
from typing import Any

from backend.engine.llm import settings as provider_settings
from backend.engine.llm.base import (
    Completion,
    LLMError,
    LLMProvider,
    LLMUnavailable,
)
from backend.engine.llm.providers import GeminiProvider, OpenAICompatibleProvider


def _cache_key(provider: str, model: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    material = "\n".join([
        provider, model, f"{temperature:.2f}", str(max_tokens), system, user,
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class LLMChain:
    """Try providers in order, reuse cached output, and expose safe errors."""

    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: float = 60,
        use_cache: bool = True,
    ) -> None:
        self.providers = providers
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.use_cache = use_cache
        self.errors: list[dict[str, Any]] = []
        self.cache_hits = 0
        self.used_provider = ""
        self.used_model = ""

    @property
    def available(self) -> bool:
        return bool(self.providers)

    def names(self) -> list[str]:
        return [provider.name for provider in self.providers]

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Completion:
        if not self.providers:
            raise LLMUnavailable([])
        heat = self.temperature if temperature is None else temperature
        limit = self.max_tokens if max_tokens is None else max_tokens

        if self.use_cache:
            try:
                from backend.db import repository

                for provider in self.providers:
                    key = _cache_key(
                        provider.name, provider.model, system, user, heat, limit
                    )
                    cached = repository.cache_get(key)
                    if cached:
                        self.cache_hits += 1
                        self.used_provider = provider.name
                        self.used_model = provider.model
                        return Completion(
                            text=cached,
                            provider=provider.name,
                            model=provider.model,
                            cached=True,
                        )
            except Exception:
                pass

        failures: list[dict[str, Any]] = []
        for provider in self.providers:
            try:
                text = provider.rewrite(
                    system,
                    user,
                    params={"temperature": heat, "max_tokens": limit},
                    temperature=heat,
                    max_tokens=limit,
                    timeout=self.timeout,
                )
            except LLMError as exc:
                failures.append({
                    "provider": provider.name,
                    "error": str(exc),
                    "status": exc.status,
                })
                self.errors.append(failures[-1])
                continue
            except Exception as exc:  # defensive: never leak a provider crash
                failures.append({
                    "provider": provider.name,
                    "error": f"Unexpected error ({type(exc).__name__})",
                    "status": None,
                })
                self.errors.append(failures[-1])
                continue
            self.used_provider = provider.name
            self.used_model = provider.model
            if self.use_cache:
                try:
                    from backend.db import repository

                    repository.cache_put(
                        _cache_key(provider.name, provider.model, system, user, heat, limit),
                        f"{provider.name}:{provider.model}",
                        text,
                    )
                except Exception:
                    pass
            return Completion(text=text, provider=provider.name, model=provider.model)

        self.errors.extend(failures)
        raise LLMUnavailable(failures)

def build_provider(provider: str) -> LLMProvider | None:
    spec = provider_settings.PROVIDERS.get(provider)
    if spec is None:
        return None
    key = provider_settings.api_key(provider)
    if not key:
        return None
    model = provider_settings.model_for(provider)
    if spec.protocol == "gemini":
        return GeminiProvider(key, model, spec.base_url)
    headers = {"X-Title": "Phrasia"}
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://127.0.0.1:8000"
    return OpenAICompatibleProvider(
        spec.id, spec.base_url, key, model, extra_headers=headers
    )


def build_chain(preferred: str = "auto") -> LLMChain:
    settings = provider_settings.load_settings()
    if not settings["enabled"]:
        return LLMChain([])
    providers: list[LLMProvider] = []
    for provider in provider_settings.provider_order(preferred):
        instance = build_provider(provider)
        if instance is not None:
            providers.append(instance)
    return LLMChain(
        providers,
        temperature=float(settings["temperature"]),
        max_tokens=int(settings["max_tokens"]),
        timeout=float(settings["timeout_seconds"]),
    )
