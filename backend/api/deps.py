"""Shared API dependencies."""
from __future__ import annotations


async def require_owner() -> None:
    """Owner gate used by every router.

    Phrasia currently binds to 127.0.0.1 only, so this is intentionally a no-op.
    TODO: replace with a real session/token check before exposing the app beyond
    localhost.
    """
    return None
