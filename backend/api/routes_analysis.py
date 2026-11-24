"""Plagiarism/similarity check, reference library and the local style signal."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.api.schemas import ReferenceRequest, TextRequest
from backend.config import MAX_UPLOAD_BYTES
from backend.db import repository
from backend.core import detector, documents, plagiarism

router = APIRouter(prefix="/api", tags=["analysis"], dependencies=[Depends(require_owner)])


def _record(kind: str, text: str, result: dict[str, Any]) -> None:
    repository.add_analysis(kind, " ".join(text.split())[:280], json.dumps(result))


@router.post("/plagiarism/check")
async def check_plagiarism(payload: TextRequest) -> dict[str, Any]:
    references = repository.reference_documents_with_content()
    result = plagiarism.check(payload.text, references)
    result["web"] = await asyncio.to_thread(plagiarism.web_check, payload.text)
    _record("plagiarism", payload.text, result)
    return result


@router.get("/plagiarism/references")
async def list_references() -> dict[str, Any]:
    return {"references": repository.list_reference_documents()}


@router.post("/plagiarism/references", status_code=201)
async def add_reference(payload: ReferenceRequest) -> dict[str, Any]:
    text = payload.text.strip()
    if not text:
        raise fail(422, "The reference text is empty.", "invalid_input")
    title = (payload.title or "").strip() or "Untitled reference"
    reference_id = repository.add_reference_document(
        title[:200], text, len(text.split())
    )
    return {
        "id": reference_id,
        "title": title[:200],
        "word_count": len(text.split()),
    }


@router.post("/plagiarism/references/upload", status_code=201)
async def upload_reference(
    request: Request,
    filename: str = Query(default="reference.txt", max_length=255),
) -> dict[str, Any]:
    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        raise fail(413, "That file is too large.", "file_too_large")
    try:
        text = documents.extract_text(filename, body)
    except ValueError as exc:
        raise fail(422, str(exc), "unreadable_file") from exc

    fallback = filename.rsplit(".", 1)[0] or "Untitled reference"
    title = fallback[:200]
    reference_id = repository.add_reference_document(title, text, len(text.split()))
    return {"id": reference_id, "title": title, "word_count": len(text.split())}


@router.delete("/plagiarism/references/{reference_id}")
async def delete_reference(reference_id: int) -> dict[str, Any]:
    if not repository.delete_reference_document(reference_id):
        raise fail(404, "That reference does not exist.", "not_found")
    return {"deleted": True, "reference_id": reference_id}


@router.post("/detector/check")
async def detect_style(payload: TextRequest) -> dict[str, Any]:
    result = detector.analyze(payload.text)
    _record("detector", payload.text, result)
    return result
