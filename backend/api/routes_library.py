"""Document history: list, reopen, delete."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.db import repository

router = APIRouter(prefix="/api", tags=["library"], dependencies=[Depends(require_owner)])


@router.get("/documents")
async def list_documents(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    return {"documents": repository.list_documents(limit)}


@router.get("/documents/{document_id}")
async def get_document(document_id: int) -> dict[str, Any]:
    document = repository.get_document(document_id)
    if document is None:
        raise fail(404, "That document does not exist.", "not_found")
    versions = repository.list_versions(document_id)
    latest_content = ""
    if versions:
        latest = repository.get_version(int(versions[0]["id"]))
        if latest is not None:
            latest_content = str(latest["content"])
    document["versions"] = versions
    document["jobs"] = repository.list_jobs_for_document(document_id)
    document["content"] = latest_content
    return document


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int) -> dict[str, Any]:
    if not repository.delete_document(document_id):
        raise fail(404, "That document does not exist.", "not_found")
    return {"deleted": True, "document_id": document_id}
