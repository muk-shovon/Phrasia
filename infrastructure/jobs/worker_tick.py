"""Worker tick endpoint for Vercel-supplied cron-driven background processing."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

# Minimal singleton registry for state during a single worker invocation.
# In production this would use Supabase directly; this file persists the contract.
_WORKER_STATE_PATH = Path(os.environ.get("WORKER_STATE_DIR", "/tmp/phrasia_worker"))
_WORKER_STATE_PATH.mkdir(parents=True, exist_ok=True)


def load_checkpoint(job_id: str) -> dict[str, Any]:
    path = _WORKER_STATE_PATH / f"{job_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"completed_chunks": {}, "failed_chunks": [], "status": "unknown"}


def save_checkpoint(job_id: str, data: dict[str, Any]) -> None:
    path = _WORKER_STATE_PATH / f"{job_id}.json"
    path.write_text(json.dumps(data))