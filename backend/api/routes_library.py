"""Document history: list, reopen, delete, plus text extraction for uploads."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.config import MAX_UPLOAD_BYTES
from backend.db import repository
from backend.core import documents

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


@router.post("/documents/extract")
async def extract_document(
    request: Request,
    filename: str = Query(default="upload.txt", max_length=255),
) -> dict[str, Any]:
    """Read a raw request body as a TXT/MD/DOCX file and return its text.

    The browser sends the File object directly, so no multipart dependency is
    needed. Nothing is stored: the caller decides whether to humanize it.
    """
    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        raise fail(413, "That file is too large.", "file_too_large")
    try:
        text = documents.extract_text(filename, body)
    except ValueError as exc:
        raise fail(422, str(exc), "unreadable_file") from exc
    return {
        "filename": filename,
        "text": text,
        "word_count": len(text.split()),
        "char_count": len(text),
    }
