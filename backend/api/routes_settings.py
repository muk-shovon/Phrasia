"""Provider settings, key storage and connection tests."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.api.schemas import KeyRequest, ProviderRequest, SettingsUpdate
from backend.db import repository
from backend.engine.llm import settings as provider_settings
from backend.engine.llm.base import LLMError
from backend.engine.llm.prompts import build_probe
from backend.engine.llm.providers import GeminiProvider, OpenAICompatibleProvider

router = APIRouter(prefix="/api", tags=["settings"], dependencies=[Depends(require_owner)])


@router.get("/settings")
def read_settings() -> dict[str, Any]:
    return provider_settings.public_settings()


@router.put("/settings")
def write_settings(payload: SettingsUpdate) -> dict[str, Any]:
    patch = payload.model_dump(exclude_none=True)
    return provider_settings.save_settings(patch)


@router.post("/settings/keys")
def store_key(payload: KeyRequest) -> dict[str, Any]:
    try:
        provider_settings.save_key(payload.provider, payload.api_key)
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc
    return {
        "saved": True,
        "provider": payload.provider,
        "configured": True,
        "key_source": provider_settings.key_source(payload.provider),
    }


@router.delete("/settings/keys/{provider}")
def remove_key(provider: str) -> dict[str, Any]:
    try:
        provider_settings.delete_key(provider)
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc
    return {"deleted": True, "provider": provider}


def _instance(provider: str, key_override: str | None = None) -> Any:
    spec = provider_settings.PROVIDERS.get(provider)
    if spec is None:
        return None
    key = (key_override or "").strip() or provider_settings.api_key(provider)
    if not key:
        return None
    model = provider_settings.model_for(provider)
    if spec.protocol == "gemini":
        return GeminiProvider(key, model, spec.base_url)
    return OpenAICompatibleProvider(spec.id, spec.base_url, key, model)


@router.post("/settings/test")
def test_provider(payload: ProviderRequest) -> dict[str, Any]:
    if payload.provider not in provider_settings.PROVIDERS:
        raise fail(422, "Unknown provider.", "invalid_input")
    instance = _instance(payload.provider, payload.api_key)
    if instance is None:
        return {
            "ok": False,
            "provider": payload.provider,
            "error": "Add a key for this provider first.",
        }
    system, user = build_probe()
    started = time.perf_counter()
    try:
        reply = instance.rewrite(
            system, user, temperature=0.0, max_tokens=16, timeout=25
        )
    except LLMError as exc:
        return {
            "ok": False,
            "provider": payload.provider,
            "model": instance.model,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "provider": payload.provider,
            "model": instance.model,
            "error": f"Connection failed ({type(exc).__name__}).",
        }
    latency = round((time.perf_counter() - started) * 1000)
    return {
        "ok": bool(reply.strip()),
        "provider": payload.provider,
        "model": instance.model,
        "latency_ms": latency,
        "reply": reply.strip()[:40],
    }


@router.post("/settings/cache/clear")
def clear_cache() -> dict[str, Any]:
    return {"deleted": repository.cache_clear()}
