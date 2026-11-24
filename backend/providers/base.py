"""Provider contract plus shared HTTP retry/error handling."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx


class ProviderFailure(Exception):
    """A safe, user-facing provider error. Never includes API keys."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        retryable: bool = False,
        status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.status = status


@dataclass
class GenerationRequest:
    text: str
    system: str
    model: str
    max_tokens: int
    temperature: float = 0.4
    timeout: float = 60.0


@dataclass
class GenerationResult:
    text: str
    provider_id: str
    model_id: str
    finish_reason: str = "stop"


class Provider(ABC):
    provider_id: str
    model: str

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        ...

    @abstractmethod
    async def health(self) -> tuple[bool, str]:
        ...


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def classify_status(status: int) -> tuple[str, bool]:
    if status == 429:
        return "rate_limited", True
    if status in {401, 403}:
        return "invalid_key", False
    if status == 404:
        return "model_or_endpoint_not_found", False
    if status in _RETRYABLE_STATUS:
        return "provider_unavailable", True
    return "request_rejected", False


async def post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout: float,
    max_attempts: int = 3,
) -> dict[str, object]:
    """POST JSON with bounded exponential backoff.

    Only retryable failures are retried. Error messages never include the
    response body or request headers, so keys cannot leak into logs or the UI.
    """
    delay = 0.6
    last_error: ProviderFailure | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            last_error = ProviderFailure(
                "The provider did not respond before the timeout.",
                code="timeout",
                retryable=True,
            )
        except httpx.HTTPError:
            last_error = ProviderFailure(
                "Could not reach the provider. Check your internet connection.",
                code="network_error",
                retryable=True,
            )
        else:
            if response.status_code < 400:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ProviderFailure(
                        "The provider returned a malformed response.",
                        code="bad_response",
                    ) from exc
                if not isinstance(data, dict):
                    raise ProviderFailure(
                        "The provider returned an unexpected response.",
                        code="bad_response",
                    )
                return data

            code, retryable = classify_status(response.status_code)
            last_error = ProviderFailure(
                f"The provider returned HTTP {response.status_code}.",
                code=code,
                retryable=retryable,
                status=response.status_code,
            )
            if not retryable or attempt == max_attempts:
                raise last_error

        if attempt < max_attempts:
            await asyncio.sleep(delay)
            delay *= 2

    raise last_error or ProviderFailure("The provider request failed.", code="provider_error")


async def get_json(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float = 10.0,
) -> tuple[int, dict[str, object] | None]:
    """Small helper for provider health checks. Returns (status, json-or-None)."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise ProviderFailure(
            "Could not reach the provider.", code="network_error", retryable=True
        ) from exc
    data: dict[str, object] | None = None
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                data = parsed
        except ValueError:
            data = None
    return response.status_code, data
