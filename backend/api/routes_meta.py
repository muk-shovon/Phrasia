"""Small informational endpoints: metadata and health."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.config import CHUNK_CHARS, MAX_INPUT_CHARS, MAX_UPLOAD_BYTES, PAID_MODELS_ENABLED
from backend.providers import catalog
from backend.core import detector, plagiarism
from backend.core.prompt import meta_payload

router = APIRouter(prefix="/api", tags=["meta"], dependencies=[Depends(require_owner)])

APP_VERSION = "0.2.0"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@router.get("/meta")
async def meta() -> dict[str, Any]:
    return {
        "version": APP_VERSION,
        **meta_payload(),
        "paid_models_enabled": PAID_MODELS_ENABLED,
        "limits": {
            "max_input_chars": MAX_INPUT_CHARS,
            "chunk_chars": CHUNK_CHARS,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
        "providers": [
            {
                "id": spec.id,
                "name": spec.name,
                "tier": spec.tier,
                "notes": spec.notes,
                "models": catalog.models_for(spec.id),
            }
            for spec in catalog.PROVIDERS
        ],
        "disclaimers": {
            "detector": detector.DISCLAIMER,
            "plagiarism": plagiarism.DISCLAIMER,
        },
    }
