"""Provider error taxonomy and normalization."""
from __future__ import annotations

from typing import Optional

from phrasia_domain import ProviderErrorCategory


class ProviderError(Exception):
    def __init__(
        self,
        category: ProviderErrorCategory,
        message: str,
        *,
        status_code: Optional[int] = None,
        provider_request_id: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.category = category
        self.message = message
        self.status_code = status_code
        self.provider_request_id = provider_request_id
        self.retry_after_seconds = retry_after_seconds
        self.retryable = retryable


def normalize_http_error(
    status_code: int,
    body_text: str,
    *,
    provider_request_id: Optional[str] = None,
) -> ProviderError:
    """Map an HTTP status code + body to a normalized ProviderError."""
    body_lower = (body_text or "").lower()
    if status_code in (401, 403):
        cat = ProviderErrorCategory.AUTHENTICATION_ERROR
        retryable = False
    elif status_code == 402:
        cat = ProviderErrorCategory.BILLING_REQUIRED
        retryable = False
    elif status_code == 404:
        cat = ProviderErrorCategory.MODEL_UNAVAILABLE
        retryable = False
    elif status_code == 413:
        cat = ProviderErrorCategory.INVALID_REQUEST
        retryable = False
    elif status_code == 429:
        cat = ProviderErrorCategory.RATE_LIMITED
        retryable = True
    elif 500 <= status_code < 600:
        cat = ProviderErrorCategory.TRANSIENT_PROVIDER_ERROR
        retryable = True
    else:
        cat = ProviderErrorCategory.UNKNOWN_PROVIDER_ERROR
        retryable = False

    if "quota" in body_lower or "exhausted" in body_lower or "rate" in body_lower:
        if status_code == 429:
            cat = ProviderErrorCategory.QUOTA_EXHAUSTED if "quota" in body_lower else cat
    return ProviderError(
        category=cat,
        message=f"Provider returned HTTP {status_code}: {body_text[:500]}",
        status_code=status_code,
        provider_request_id=provider_request_id,
        retryable=retryable,
    )