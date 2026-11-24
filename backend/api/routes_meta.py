"""Small informational endpoints: metadata and health."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.config import CHUNK_CHARS, MAX_INPUT_CHARS, MAX_UPLOAD_BYTES
from backend.core import detector, plagiarism
from backend.core.prompt import meta_payload
from backend.providers import catalog

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
        "limits": {
            "max_input_chars": MAX_INPUT_CHARS,
            "chunk_chars": CHUNK_CHARS,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
        "providers": [
            {
                "id": spec.id,
                "name": spec.name,
                "base_url": spec.base_url,
                "model": spec.model,
                "anonymous": spec.anonymous,
                "rate_limit_requests_per_minute": spec.rate_limit_requests_per_minute,
                "max_chunk_tokens": spec.max_chunk_tokens,
            }
            for spec in catalog.PROVIDERS
        ],
        "disclaimers": {
            "detector": detector.DISCLAIMER,
            "plagiarism": plagiarism.DISCLAIMER,
            "web": plagiarism.DISCLAIMER_WEB,
        },
    }
