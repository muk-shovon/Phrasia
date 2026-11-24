"""Single source of truth for provider specs and the model catalog.

Every provider here must be anonymous-first: Phrasia never asks for a user API
key. Providers with rate limits (e.g. the anonymous OVH lane) declare a
``rate_limit_requests_per_minute`` value used by the per-provider limiter in
``backend/providers/base.py``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    base_url: str
    model: str
    priority: int
    notes: str
    anonymous: bool = True
    enabled: bool = True
    requires_key: bool = False
    rate_limit_requests_per_minute: int = 10
    max_chunk_tokens: int = 800


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        id="pollinations",
        name="Pollinations (anonymous, free)",
        base_url="https://text.pollinations.ai/openai",
        model="gpt-oss-20b",
        priority=10,
        notes="Verified anonymous in 2026-11: rewrite of ~300 words in ~8s.",
        rate_limit_requests_per_minute=60,
    ),
    ProviderSpec(
        id="ovh",
        name="OVHcloud AI Endpoints (anonymous)",
        base_url="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        model="gpt-oss-20b",
        priority=20,
        notes="Anonymous OpenAI-compatible lane; probe showed ~2 req/min behaviour (rate-limited at times).",
        rate_limit_requests_per_minute=2,
    ),
)


def get_spec(provider_id: str) -> ProviderSpec | None:
    return next((spec for spec in PROVIDERS if spec.id == provider_id), None)


def enabled_providers() -> tuple[ProviderSpec, ...]:
    return tuple(spec for spec in PROVIDERS if spec.enabled)
