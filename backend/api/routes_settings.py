"""Provider configuration and owner preferences."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.api.errors import UnsafeEndpoint, fail, validate_base_url
from backend.api.schemas import PreferencesUpdate, ProviderUpdate
from backend.config import CHUNK_CHARS, DB_PATH, MAX_INPUT_CHARS, MAX_UPLOAD_BYTES
from backend.db import repository
from backend.providers import catalog
from backend.providers.base import get_json
from backend.providers.registry import ProviderRegistry

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_owner)])


@router.get("")
async def get_settings() -> dict[str, Any]:
    registry = ProviderRegistry()
    return {
        "providers": registry.settings_view(),
        "preferred_provider": registry.preferred_provider_id(),
        "paid_models_enabled": False,
        "database_path": str(DB_PATH),
        "limits": {
            "max_input_chars": MAX_INPUT_CHARS,
            "chunk_chars": CHUNK_CHARS,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
    }


@router.put("/providers/{provider_id}")
async def update_provider(provider_id: str, payload: ProviderUpdate) -> dict[str, Any]:
    spec = catalog.get_spec(provider_id)
    if spec is None:
        raise fail(404, "Unknown provider.", "unknown_provider")

    base_url = payload.base_url
    if base_url:
        try:
            base_url = validate_base_url(base_url)
        except UnsafeEndpoint as exc:
            raise fail(422, str(exc), "unsafe_base_url") from exc

    api_key = payload.api_key if payload.api_key else None
    repository.upsert_provider_setting(
        provider_id,
        api_key=api_key.strip() if api_key else None,
        model=payload.model,
        base_url=base_url,
        enabled=payload.enabled,
    )
    provider = ProviderRegistry().resolve(provider_id)
    return {"provider": _provider_card(provider_id, provider)}


def _provider_card(provider_id: str, provider: Any) -> dict[str, Any]:
    registry = ProviderRegistry()
    card = next(
        (item for item in registry.settings_view() if item["id"] == provider_id), None
    )
    if card is None:
        raise fail(404, "Unknown provider.", "unknown_provider")
    enabled = repository.provider_setting(provider_id) or {}
    card["enabled"] = int(enabled.get("enabled")) if enabled.get("enabled") is not None else 1
    return card


@router.post("/providers/{provider_id}/models")
async def list_provider_models(provider_id: str) -> dict[str, Any]:
    """Ask a provider what models exist (calls GET /models). Mocked in tests."""
    configured = ProviderRegistry().resolve(provider_id)
    if configured is None:
        raise fail(404, "This provider is not configured.", "not_configured")
    status, data = await get_json(
        f"{configured.provider.base_url}/models",
        headers=configured.provider._headers(),  # type: ignore[attr-defined]
    )
    if status == 200 and data is not None:
        entries = data.get("data", data.get("models", []))
        if isinstance(entries, list):
            models = [
                {"id": str(item.get("id") or item.get("name") or ""), "label": str(item.get("id") or item.get("name") or "")}
                for item in entries
                if isinstance(item, dict) and (item.get("id") or item.get("name"))
            ]
            return {"provider_id": provider_id, "models": models[:50]}
        raise fail(502, "The provider returned no model list.", "no_model_list")
    raise fail(502, f"Provider returned HTTP {status}.", "provider_error")


@router.delete("/providers/{provider_id}/key")
async def clear_provider_key(provider_id: str) -> dict[str, Any]:
    if catalog.get_spec(provider_id) is None:
        raise fail(404, "Unknown provider.", "unknown_provider")
    repository.delete_provider_key(provider_id)
    return {"cleared": True, "provider_id": provider_id}


@router.post("/providers/{provider_id}/test")
async def test_provider(provider_id: str) -> dict[str, Any]:
    if catalog.get_spec(provider_id) is None:
        raise fail(404, "Unknown provider.", "unknown_provider")
    ok, message = await ProviderRegistry().test(provider_id)
    return {"ok": ok, "message": message}


@router.put("/preferences")
async def update_preferences(payload: PreferencesUpdate) -> dict[str, Any]:
    value = (payload.preferred_provider or "").strip()
    if value and catalog.get_spec(value) is None:
        raise fail(422, "Unknown provider.", "unknown_provider")
    repository.set_preference("preferred_provider", value)
    return {"preferred_provider": value or None}
