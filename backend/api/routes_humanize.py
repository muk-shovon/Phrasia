"""Synchronous local rewriting plus text and DOCX export."""
from __future__ import annotations

import difflib
import re
from typing import Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.api.schemas import ExportRequest, HumanizeRequest
from backend.core import humanizer
from backend.core.documents import export_docx, safe_filename
from backend.core.rewrite_diff import diff_from_alignment
from backend.db import repository

router = APIRouter(prefix="/api", tags=["humanize"], dependencies=[Depends(require_owner)])
_WORD = re.compile(r"\S+")


def _words_changed_pct(original: str, rewritten: str) -> int:
    source = [word.lower() for word in _WORD.findall(original)]
    result = [word.lower() for word in _WORD.findall(rewritten)]
    matcher = difflib.SequenceMatcher(None, source, result, autojunk=False)
    unchanged = sum(block.size for block in matcher.get_matching_blocks())
    changed = max(len(source), len(result)) - unchanged
    return min(100, round(100 * changed / max(len(source), 1)))


def _title(text: str) -> str:
    words = text.strip().split()[:8]
    return " ".join(words) or "Untitled document"


@router.post("/humanize")
async def create_humanization(payload: HumanizeRequest) -> JSONResponse:
    try:
        result = humanizer.humanize(
            payload.text,
            tone=payload.tone,
            strength=payload.strength,
            variation=payload.variation,
            clean_invisible=payload.clean_invisible,
            replace_dashes=payload.replace_dashes,
            straight_quotes=payload.straight_quotes,
        )
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc

    alignment = result["alignment"]
    segments = diff_from_alignment(alignment)
    changed = sum(1 for segment in segments if segment.get("type") == "changed")
    review = sum(
        1
        for segment in segments
        if segment.get("type") == "changed" and segment.get("risk") in {"meaning", "number"}
    )
    document_id = repository.create_document(_title(payload.text)[:200])
    repository.add_version(document_id, "source", payload.text)
    repository.add_version(document_id, "humanized", result["text"])

    body: dict[str, Any] = {
        "rewritten": result["text"],
        "sentences": result["sentences"],
        "diff": {"segments": segments, "changed": changed, "review": review},
        "style_check": {
            "sentences_restructured": result["summary"]["sentences_restructured"],
            "sentences_total": result["summary"]["sentences_total"],
            "words_changed_pct": _words_changed_pct(payload.text, result["text"]),
        },
        "report": result["report"],
        "document_id": document_id,
    }
    return JSONResponse(body, media_type="application/json; charset=utf-8")


@router.post("/export")
async def export_text(payload: ExportRequest) -> Response:
    title = (payload.title or "").strip() or "phrasia"
    return Response(
        content=payload.text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename(title, "txt")}"'},
    )


@router.post("/export/docx")
async def export_document(payload: ExportRequest) -> Response:
    title = (payload.title or "").strip() or "phrasia"
    return Response(
        content=export_docx(payload.text),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename(title, "docx")}"'},
    )
