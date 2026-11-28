"""In-memory progress jobs for hosted rewriting.

The synchronous ``/api/humanize`` endpoint stays available for scripts. The
web UI starts a job so it can show which pass is running.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable

JobRunner = Callable[[Callable[[str, int, int, str], None]], dict[str, Any]]
_TTL_SECONDS = 900
_MAX_JOBS = 40


class Job:
    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.status = "queued"
        self.stage = "queued"
        self.current = 0
        self.total = 0
        self.message = "Waiting to start"
        self.result: dict[str, Any] | None = None
        self.error: str | None = None
        self.code = ""
        self.created_at = time.time()
        self.updated_at = self.created_at

    def progress(self, stage: str, current: int, total: int, message: str) -> None:
        self.status = "running"
        self.stage = stage
        self.current = int(current)
        self.total = int(total)
        self.message = message
        self.updated_at = time.time()

    def as_dict(self, *, include_result: bool = True) -> dict[str, Any]:
        body: dict[str, Any] = {
            "job_id": self.id,
            "status": self.status,
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "code": self.code,
        }
        if include_result and self.result is not None:
            body["result"] = self.result
        return body


_JOBS: dict[str, Job] = {}
_LOCK = threading.Lock()


def _prune() -> None:
    now = time.time()
    expired = [
        key for key, job in _JOBS.items()
        if now - job.updated_at > _TTL_SECONDS
    ]
    for key in expired:
        _JOBS.pop(key, None)
    if len(_JOBS) > _MAX_JOBS:
        oldest = sorted(_JOBS, key=lambda key: _JOBS[key].created_at)
        for key in oldest[: len(_JOBS) - _MAX_JOBS]:
            _JOBS.pop(key, None)


def start(runner: JobRunner) -> str:
    _prune()
    job = Job()
    with _LOCK:
        _JOBS[job.id] = job

    def work() -> None:
        job.status = "running"
        try:
            job.result = runner(job.progress)
            job.status = "done"
            job.stage = "done"
            job.message = "Rewrite complete"
            job.current = job.total or 1
            job.total = job.total or 1
        except ValueError as exc:
            job.status = "error"
            job.stage = "error"
            job.message = "Rewrite failed"
            job.error = str(exc)
            job.code = "invalid_input"
        except Exception as exc:  # provider and network failures land here
            job.status = "error"
            job.stage = "error"
            job.message = "Rewrite failed"
            job.error = str(exc) or "The hosted provider could not finish this request."
            job.code = "provider_error"
        job.updated_at = time.time()

    threading.Thread(target=work, daemon=True, name=f"humanize-{job.id[:8]}").start()
    return job.id


def get(job_id: str) -> Job | None:
    _prune()
    return _JOBS.get(job_id)
