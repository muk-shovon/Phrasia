"""Fetch the live model catalog for each generation provider.

Most providers expose a ``/models`` endpoint. OpenRouter additionally returns
per-model pricing, which lets us tell free models from paid ones exactly; for
providers that do not publish pricing we use a conservative, documented
heuristic and label the result so the UI can explain it to the user.

Raw API keys are only used for the outbound request — they never appear in the
returned :class:`ModelCatalog` or in any UI state.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Models offered per provider when the live endpoint is unavailable (no key,
# offline gateway, network error). Each entry is (model_id, "free"|"paid").
FALLBACK_MODELS: dict[str, list[tuple[str, str]]] = {
    "gemini": [
        ("gemini-2.5-flash", "free"),
        ("gemini-2.5-flash-lite", "free"),
        ("gemini-2.5-pro", "paid"),
        ("gemini-2.0-flash", "free"),
        ("gemini-2.0-flash-lite", "free"),
        ("gemini-1.5-flash", "free"),
        ("gemini-1.5-pro", "paid"),
    ],
    "groq": [
        ("llama-3.3-70b-versatile", "free"),
        ("llama-3.1-8b-instant", "free"),
        ("openai/gpt-oss-120b", "free"),
        ("openai/gpt-oss-20b", "free"),
        ("mixtral-8x7b-32768", "free"),
        ("gemma2-9b-it", "free"),
        ("deepseek-r1-distill-llama-70b", "free"),
    ],
    "openrouter": [
        ("openrouter/auto", "free"),
        ("google/gemini-2.0-flash-001", "free"),
        ("meta-llama/llama-3.3-70b-instruct:free", "free"),
        ("deepseek/deepseek-chat", "paid"),
        ("anthropic/claude-3.5-sonnet", "paid"),
        ("openai/gpt-4o-mini", "paid"),
    ],
    "freellmapi": [
        ("auto", "free"),
        ("auto:fast", "free"),
    ],
    "openai": [
        ("gpt-4.1-mini", "paid"),
        ("gpt-4.1", "paid"),
        ("gpt-4o-mini", "paid"),
        ("gpt-4o", "paid"),
        ("o3-mini", "paid"),
    ],
    "anthropic": [
        ("claude-3-5-haiku-20241022", "paid"),
        ("claude-3-5-sonnet-20241022", "paid"),
        ("claude-3-7-sonnet-20250219", "paid"),
        ("claude-sonnet-4-20250514", "paid"),
    ],
    "custom": [],
}


@dataclass
class ModelInfo:
    id: str
    name: str = ""
    tier: str = "unknown"  # free | paid | unknown
    note: str = ""
    context_length: Optional[int] = None
    available: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name or self.id,
            "tier": self.tier,
            "note": self.note,
            "context_length": self.context_length,
            "available": self.available,
        }


@dataclass
class ModelCatalog:
    models: list[ModelInfo] = field(default_factory=list)
    source: str = "live"  # live | fallback
    error: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "models": [m.as_dict() for m in self.models],
            "source": self.source,
            "error": self.error,
            "note": self.note,
        }


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify(
    provider_id: str,
    model_id: str,
    *,
    provider_tier: str = "",
    pricing: Optional[dict] = None,
) -> str:
    """Return ``"free"``, ``"paid"`` or ``"unknown"`` for one model id.

    OpenRouter exposes exact per-model pricing, so that is authoritative.
    Other providers don't publish prices on ``/models``; for those we use a
    small, explicit heuristic and the UI labels the result as approximate.
    """
    mid = (model_id or "").lower()

    if provider_id == "openrouter":
        p = pricing or {}
        prompt = _to_float(p.get("prompt"))
        completion = _to_float(p.get("completion"))
        if mid.endswith(":free"):
            return "free"
        if prompt is not None and completion is not None:
            return "free" if prompt == 0 and completion == 0 else "paid"
        return "unknown"

    if provider_id == "gemini":
        # Google's no-cost tier covers the Flash/Lite families; Pro and
        # experimental preview models generally require billing.
        if "lite" in mid or "flash" in mid:
            return "free"
        if "pro" in mid or "exp" in mid:
            return "paid"
        return "unknown"

    if provider_id in {"groq", "freellmapi", "custom"}:
        # Groq's free tier is rate-limited, and the other two are self-hosted.
        return "free"

    if provider_id in {"openai", "anthropic"}:
        return "paid"

    return provider_tier if provider_tier in {"free", "paid"} else "unknown"


def _fallback_catalog(provider_id: str, *, reason: str) -> ModelCatalog:
    models = [
        ModelInfo(id=mid, name=mid, tier=tier)
        for mid, tier in FALLBACK_MODELS.get(provider_id, [])
    ]
    return ModelCatalog(
        models=models,
        source="fallback",
        error=reason,
        note="Built-in list — add a key and refresh for live models.",
    )


def _parse_openai_compatible(
    data: Any, provider_id: str, provider_tier: str
) -> list[ModelInfo]:
    rows = data.get("data") or [] if isinstance(data, dict) else []
    models: list[ModelInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or "").strip()
        if not mid:
            continue
        # Some gateways list hundreds of models but require a separate key for
        # most of them. Only offer models that can actually run.
        if row.get("available") is False:
            continue
        tier = classify(provider_id, mid, provider_tier=provider_tier, pricing=row.get("pricing"))
        models.append(
            ModelInfo(
                id=mid,
                name=str(row.get("name") or mid),
                tier=tier,
                context_length=row.get("context_length"),
            )
        )
    return models


def _parse_gemini(data: Any) -> list[ModelInfo]:
    rows = data.get("models") or [] if isinstance(data, dict) else []
    models: list[ModelInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw_name = str(row.get("name") or "")
        mid = raw_name.split("/")[-1] if "/" in raw_name else raw_name
        if not mid:
            continue
        models.append(
            ModelInfo(
                id=mid,
                name=str(row.get("displayName") or mid),
                tier=classify("gemini", mid),
                note="Free/paid is approximate — Google does not publish prices here.",
                context_length=row.get("inputTokenLimit"),
            )
        )
    return models


def _parse_anthropic(data: Any) -> list[ModelInfo]:
    rows = data.get("data") or [] if isinstance(data, dict) else []
    models: list[ModelInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("id") or "").strip()
        if not mid:
            continue
        models.append(
            ModelInfo(
                id=mid,
                name=str(row.get("display_name") or mid),
                tier=classify("anthropic", mid),
            )
        )
    return models


async def fetch_models(
    provider_id: str,
    *,
    base_url: str,
    api_key: str = "",
    provider_tier: str = "",
    timeout: float = 15.0,
) -> ModelCatalog:
    """Fetch and classify the model list. Never raises on network errors."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return _fallback_catalog(
            provider_id, reason="No base URL configured. Set one above to fetch models."
        )

    if provider_id == "gemini":
        url = f"{base}/models"
        headers = {"x-goog-api-key": api_key} if api_key else {}
    elif provider_id == "anthropic":
        url = f"{base}/models"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    else:
        url = f"{base}/models"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            if not 200 <= response.status_code < 300:
                return _fallback_catalog(
                    provider_id,
                    reason=f"HTTP {response.status_code} from model endpoint",
                )
            data = response.json()
    except Exception as exc:
        logger.debug("Model fetch failed for %s: %s", provider_id, exc)
        return _fallback_catalog(provider_id, reason=f"{type(exc).__name__}: {exc}"[:160])

    if provider_id == "gemini":
        models = _parse_gemini(data)
    elif provider_id == "anthropic":
        models = _parse_anthropic(data)
    else:
        models = _parse_openai_compatible(data, provider_id, provider_tier)

    if not models:
        return _fallback_catalog(provider_id, reason="Endpoint returned no models")

    note = ""
    if provider_id == "openrouter":
        note = "Free/paid from live OpenRouter pricing."
    elif provider_id in {"gemini", "groq"}:
        note = "Free/paid is a best-effort label; the API does not publish prices."

    return ModelCatalog(models=models, source="live", note=note)
