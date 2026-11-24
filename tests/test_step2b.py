"""Step A2: anonymous-first catalog, rate limiter, settings, masked keys."""
from __future__ import annotations

from backend.providers import base
from backend.providers.catalog import PROVIDERS, get_spec
from backend.providers.base import ProviderFailure, RateLimiter


def test_catalog_is_anonymous_first() -> None:
    assert PROVIDERS, "catalog must not be empty"
    for spec in PROVIDERS:
        assert spec.anonymous, f"{spec.id} should be anonymous-first"
        assert spec.base_url.startswith("http"), "base_url should be public https/http"


def test_catalog_priority_is_fallback_order() -> None:
    priorities = [spec.priority for spec in PROVIDERS]
    assert priorities == sorted(priorities)


def test_rate_limiter_waits_and_raises() -> None:
    import asyncio

    limiter = RateLimiter()
    limiter.set_interval("test-provider", 60.0)

    # First call passes
    asyncio.run(limiter.wait_if_limited("test-provider"))

    # Immediate second call must raise rate_limited
    try:
        asyncio.run(limiter.wait_if_limited("test-provider"))
        raised = False
    except ProviderFailure as exc:
        raised = exc.code == "rate_limited"
    assert raised


def test_rate_limiter_uses_provider_spec_interval() -> None:
    limiter = base.rate_limiter_for("ovh", spec_interval=2.0)
    assert limiter._interval.get("ovh") == 2.0


def test_no_rate_limiter_for_zero_interval() -> None:
    import asyncio

    limiter = base.rate_limiter_for("pollinations-none")
    asyncio.run(limiter.wait_if_limited("pollinations-none"))  # no raise


def test_provider_settings_view_masking(client) -> None:
    client.put("/api/settings/providers/pollinations", json={"api_key": "secret-value-1234", "model": "gpt-oss-20b"})
    body = client.get("/api/settings").json()
    raw = client.get("/api/settings").text
    card = next(item for item in body["providers"] if item["id"] == "pollinations")
    assert "secret-value-1234" not in raw
    assert card["masked_key"].endswith("1234")
    assert card["anonymous"] is True


def test_get_spec_unknown() -> None:
    assert get_spec("nonexistent") is None
