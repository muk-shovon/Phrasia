"""Shared API error helper."""
from __future__ import annotations

from fastapi import HTTPException


def fail(status_code: int, message: str, code: str = "request_error") -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )
