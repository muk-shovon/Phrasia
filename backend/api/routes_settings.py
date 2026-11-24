"""Provider configuration and owner preferences."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.api.errors import UnsafeEndpoint, fail, validate_base_url
from backend.api.schemas import PreferencesUpdate, ProviderUpdate
from backend.config import (
    CHUNK_CHARS,
    DB_PATH,
    MAX_INPUT_CHARS,
    MAX_UPLOAD_BYTES,
    PAID_MODELS_ENABLED,
)
from backend.db import repository
from backend.providers import catalog
from backend.providers.registry import ProviderRegistry

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_owner)])


@router.get("")
async def get_settings() -> dict[str, Any]:
    registry = ProviderRegistry()
    return {
        "providers": registry.settings_view(),
        "preferred_provider": registry.preferred_provider_id(),
        "paid_models_enabled": PAID_MODELS_ENABLED,
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
    registry = ProviderRegistry()
    return {
        "provider": next(
            (
                item
                for item in registry.settings_view()
                if item["id"] == provider_id
            ),
            None,
        )
    }


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
