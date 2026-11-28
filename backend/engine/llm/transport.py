"""Small JSON-over-HTTP helper with bounded retries.

Only the standard library is used, so no extra package is installed and the
local machine stays light.
"""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from backend.engine.llm.base import LLMError

_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 529}


def _error_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:180]
    if isinstance(error, str) and error.strip():
        return error.strip()[:180]
    message = payload.get("message")
    return message.strip()[:180] if isinstance(message, str) else ""


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout: float,
    retries: int = 2,
    provider: str = "",
) -> dict[str, Any]:
    """POST JSON and decode the response, retrying transient failures."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Phrasia/1.0",
        **headers,
    }
    last: LLMError | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url, data=body, headers=request_headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:2000]
            except OSError:
                detail = ""
            message = _error_message(detail)
            last = LLMError(
                f"HTTP {exc.code}" + (f" ({message})" if message else ""),
                status=exc.code,
                retryable=exc.code in _RETRY_STATUS,
                provider=provider,
            )
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", None) or exc
            last = LLMError(
                f"Network error ({str(reason)[:120]})",
                retryable=True,
                provider=provider,
            )
        else:
            try:
                decoded = json.loads(raw)
            except ValueError as exc:
                raise LLMError(
                    "Provider returned invalid JSON.",
                    retryable=True,
                    provider=provider,
                ) from exc
            if not isinstance(decoded, dict):
                raise LLMError(
                    "Provider returned an unexpected payload.",
                    retryable=True,
                    provider=provider,
                )
            return decoded

        if last is None or not last.retryable or attempt >= retries:
            raise last
        time.sleep(min(6.0, 0.7 * (2 ** attempt)))
    raise last or LLMError("Provider call failed.", provider=provider)
