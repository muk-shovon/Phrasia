"""Phrasia application entrypoint.

Run locally with:  python -m backend.main
The API is served from /api/* and the built frontend from frontend/dist.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api import api_router
from backend.config import FRONTEND_DIST
from backend.db import repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("phrasia")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    repository.init_db()
    paused = repository.mark_interrupted_jobs_paused()
    if paused:
        logger.info("marked %s interrupted job(s) as paused for resume", paused)
    yield


app = FastAPI(
    title="Phrasia",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.include_router(api_router)

_ASSETS_DIR = FRONTEND_DIST / "assets"
if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")


def _build_hint() -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Phrasia — frontend not built</title>"
        "<style>body{font-family:system-ui;margin:3rem auto;max-width:38rem;"
        "line-height:1.6;color:#1d2a22}code{background:#eef1ea;padding:.15rem .35rem;"
        "border-radius:.25rem}</style></head><body>"
        "<h1>Frontend not built yet</h1>"
        "<p>The API is running. The web interface needs one build step:</p>"
        "<pre><code>cd frontend\nnpm install\nnpm run build\ncd ..</code></pre>"
        "<p>Then reload this page.</p>"
        "<p>API docs: <a href='/api/docs'>/api/docs</a></p>"
        "</body></html>"
    )


@app.get("/{path:path}", include_in_schema=False)
async def serve_frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HTMLResponse(_build_hint(), status_code=503)

    if path:
        candidate = (FRONTEND_DIST / path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found") from None
        if candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(index)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PHRASIA_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
