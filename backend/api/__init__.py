"""Phrasia HTTP API routers. Export ROUTERS for FastAPI.app.include_router."""
from __future__ import annotations

from backend.api.routes_analysis import router as analysis_router
from backend.api.routes_humanize import router as humanize_router
from backend.api.routes_library import router as library_router
from backend.api.routes_meta import router as meta_router
from backend.api.routes_settings import router as settings_router

ROUTERS = (
    analysis_router,
    humanize_router,
    library_router,
    meta_router,
    settings_router,
)
