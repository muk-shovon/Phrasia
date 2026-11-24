"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner

router = APIRouter(prefix="/api", tags=["meta"], dependencies=[Depends(require_owner)])

APP_VERSION = "1.0.0"


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}
