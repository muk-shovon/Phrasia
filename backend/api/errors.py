"""Small helpers shared by the routers."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from fastapi import HTTPException


def fail(status_code: int, message: str, code: str = "request_error") -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


class UnsafeEndpoint(ValueError):
    pass


_LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "0.0.0.0"}


def validate_base_url(value: str) -> str:
    """Reject anything that is not a public http(s) endpoint.

    Phrasia is meant to call online APIs. Blocking loopback/private targets keeps
    a typo (or a stray config) from pointing the app at a local model server.
    """
    candidate = (value or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeEndpoint("Base URL must start with http:// or https://.")
    host = parsed.hostname.lower()
    if host in _LOOPBACK_NAMES or host.endswith(".local"):
        raise UnsafeEndpoint("Base URL must be a public online endpoint.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return candidate.rstrip("/")
    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
    ):
        raise UnsafeEndpoint("Base URL must be a public online endpoint.")
    return candidate.rstrip("/")
