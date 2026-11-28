"""Rewriting, progress jobs, sentence refreshes and text/DOCX export."""
from __future__ import annotations

import difflib
import re
from typing import Any, Callable

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from backend.api import jobs
from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.api.schemas import (
    ExportRequest,
    FeedbackRequest,
    HumanizeRequest,
    SentenceRequest,
)
from backend.core import humanizer
from backend.core.documents import export_docx, safe_filename
from backend.core.rewrite_diff import diff_from_alignment
from backend.db import repository
from backend.engine.llm import LLMUnavailable

router = APIRouter(prefix="/api", tags=["humanize"], dependencies=[Depends(require_owner)])
_WORD = re.compile(r"\S+")

Progress = Callable[[str, int, int, str], None]


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


def _run_humanize(payload: HumanizeRequest, on_progress: Progress | None = None) -> dict[str, Any]:
    try:
        result = humanizer.humanize(
            payload.text,
            tone=payload.tone,
            strength=payload.strength,
            variation=payload.variation,
            clean_invisible=payload.clean_invisible,
            replace_dashes=payload.replace_dashes,
            straight_quotes=payload.straight_quotes,
            intensity=payload.intensity,
            provider=payload.provider,
            mode=payload.mode,
            offline_fallback=payload.offline_fallback,
            on_progress=on_progress,
        )
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc
    except LLMUnavailable as exc:
        raise fail(502, str(exc), "provider_error") from exc

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
    version_id = repository.add_version(document_id, "humanized", result["text"])

    return {
        "rewritten": result["text"],
        "sentences": result["sentences"],
        "diff": {"segments": segments, "changed": changed, "review": review},
        "style_check": {
            "sentences_restructured": result["summary"]["sentences_restructured"],
            "sentences_total": result["summary"]["sentences_total"],
            "words_changed_pct": _words_changed_pct(payload.text, result["text"]),
        },
        "report": result["report"],
        "meta": result.get("meta", {"mode": "offline"}),
        "document_id": document_id,
        "version_id": version_id,
    }


@router.post("/humanize")
def create_humanization(payload: HumanizeRequest) -> JSONResponse:
    body = _run_humanize(payload)
    return JSONResponse(body, media_type="application/json; charset=utf-8")


@router.post("/humanize/jobs", status_code=202)
def start_humanization(payload: HumanizeRequest) -> dict[str, Any]:
    job_id = jobs.start(lambda progress: _run_humanize(payload, progress))
    return {"job_id": job_id, "status": "queued"}


@router.get("/humanize/jobs/{job_id}")
def read_humanization_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if job is None:
        raise fail(404, "That rewrite job is not available.", "not_found")
    return job.as_dict()


@router.post("/humanize/sentence")
def refresh_sentence(payload: SentenceRequest) -> dict[str, Any]:
    try:
        result = humanizer.humanize_sentence(
            payload.text,
            tone=payload.tone,
            strength=payload.strength,
            provider=payload.provider,
            replace_dashes=payload.replace_dashes,
            straight_quotes=payload.straight_quotes,
        )
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc
    except LLMUnavailable as exc:
        raise fail(502, str(exc), "provider_error") from exc
    return result


@router.post("/feedback", status_code=201)
def record_feedback(payload: FeedbackRequest) -> dict[str, Any]:
    feedback_id = repository.add_feedback(
        version_id=payload.version_id,
        sentence_idx=payload.sentence_idx,
        action=payload.action,
        source_text=payload.source_text,
        final_text=payload.final_text,
        operation=payload.operation,
    )
    saved = False
    if payload.action in {"accepted", "edited"} and payload.final_text.strip():
        if payload.source_text.strip():
            repository.add_example_pair(
                tone=payload.tone,
                strength=payload.strength,
                operation=payload.operation,
                source_text=payload.source_text,
                rewritten_text=payload.final_text,
                rating=1,
            )
            saved = True
    return {"id": feedback_id, "saved_example": saved}


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
