"""Phrasia HTTP API routers."""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.routes_analysis import router as analysis_router
from backend.api.routes_humanize import router as humanize_router
from backend.api.routes_library import router as library_router
from backend.api.routes_meta import router as meta_router
from backend.api.routes_settings import router as settings_router

api_router = APIRouter()
api_router.include_router(meta_router)
api_router.include_router(humanize_router)
api_router.include_router(library_router)
api_router.include_router(settings_router)
api_router.include_router(analysis_router)
