"""Humanize endpoint plus job inspection, retry, cancel and export."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response

from backend.api.deps import require_owner
from backend.api.errors import fail
from backend.api.schemas import HumanizeRequest
from backend.db import repository
from backend.core import humanizer
from backend.core.documents import export_docx, safe_filename
from backend.core.prompt import HumanizeOptions

router = APIRouter(prefix="/api", tags=["humanize"], dependencies=[Depends(require_owner)])


def job_payload(detail: dict[str, Any]) -> dict[str, Any]:
    total = int(detail.get("total_chunks") or 0)
    completed = int(detail.get("completed_chunks") or 0)
    payload = {
        "id": int(detail["id"]),
        "document_id": int(detail["document_id"]),
        "title": str(detail.get("title") or "Untitled document"),
        "status": str(detail["status"]),
        "mode": str(detail["mode"]),
        "intensity": str(detail["intensity"]),
        "provider_id": detail.get("provider_id"),
        "model_id": detail.get("model_id"),
        "error": detail.get("error"),
        "total_chunks": total,
        "completed_chunks": completed,
        "progress_percent": round(100 * completed / total) if total else 0,
        "created_at": detail.get("created_at"),
        "updated_at": detail.get("updated_at"),
        "input_text": detail.get("input_text") or "",
        "output_text": detail.get("output_text"),
        "options": json.loads(str(detail.get("options_json") or "{}")),
        "chunks": detail.get("chunks") or [],
    }
    return payload


@router.post("/humanize", status_code=202)
async def create_humanization(
    payload: HumanizeRequest, background: BackgroundTasks
) -> dict[str, Any]:
    try:
        job_id = humanizer.create_job(
            payload.text,
            title=payload.title,
            mode=payload.mode,
            intensity=payload.intensity,
            options=HumanizeOptions(
                preserve_formatting=payload.preserve_formatting,
                keep_quotes=payload.keep_quotes,
                deep_humanize=payload.deep_humanize,
                remove_em_dashes=payload.remove_em_dashes,
            ),
            provider_id=payload.provider_id,
        )
    except ValueError as exc:
        raise fail(422, str(exc), "invalid_input") from exc

    background.add_task(humanizer.run_job, job_id)
    return {"job_id": job_id}


@router.get("/jobs")
async def jobs(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    return {"jobs": repository.list_jobs(limit)}


@router.get("/jobs/{job_id}")
async def job(job_id: int) -> dict[str, Any]:
    detail = repository.get_job_detail(job_id)
    if detail is None:
        raise fail(404, "That job does not exist.", "not_found")
    return job_payload(detail)


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int, background: BackgroundTasks) -> dict[str, Any]:
    if repository.get_job(job_id) is None:
        raise fail(404, "That job does not exist.", "not_found")
    if not humanizer.ensure_resumable(job_id):
        raise fail(409, "This job is already complete.", "not_resumable")
    background.add_task(humanizer.run_job, job_id)
    return {"job_id": job_id, "status": "queued"}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int) -> dict[str, Any]:
    current = repository.get_job(job_id)
    if current is None:
        raise fail(404, "That job does not exist.", "not_found")
    if current["status"] == "completed":
        raise fail(409, "This job is already complete.", "not_cancellable")
    repository.update_job(job_id, status="cancelled")
    return {"job_id": job_id, "status": "cancelled"}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: int) -> dict[str, Any]:
    if not repository.delete_job(job_id):
        raise fail(404, "That job does not exist.", "not_found")
    return {"deleted": True, "job_id": job_id}


@router.get("/jobs/{job_id}/export")
async def export_job(
    job_id: int, fmt: str = Query(default="txt", alias="format")
) -> Response:
    detail = repository.get_job_detail(job_id)
    if detail is None:
        raise fail(404, "That job does not exist.", "not_found")
    text = detail.get("output_text")
    if not text:
        raise fail(409, "This job has no finished output to export.", "not_ready")

    title = str(detail.get("title") or "phrasia")
    kind = (fmt or "txt").lower()
    if kind == "txt":
        body = str(text).encode("utf-8")
        media = "text/plain; charset=utf-8"
        filename = safe_filename(title, "txt")
    elif kind == "docx":
        body = export_docx(str(text))
        media = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = safe_filename(title, "docx")
    else:
        raise fail(422, "Supported export formats are txt and docx.", "bad_format")

    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
