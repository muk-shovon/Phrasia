"""Tests for the live model catalog and free/paid classification."""
from __future__ import annotations

import pytest

from providers.model_catalog import (
    FALLBACK_MODELS,
    ModelCatalog,
    ModelInfo,
    _fallback_catalog,
    _parse_gemini,
    _parse_openai_compatible,
    classify,
    fetch_models,
)


def test_openrouter_pricing_is_authoritative() -> None:
    assert (
        classify(
            "openrouter",
            "deepseek/deepseek-chat",
            pricing={"prompt": "0", "completion": "0"},
        )
        == "free"
    )
    assert (
        classify(
            "openrouter",
            "openai/gpt-4o",
            pricing={"prompt": "0.000005", "completion": "0.000015"},
        )
        == "paid"
    )
    assert classify("openrouter", "some/model:free") == "free"
    assert classify("openrouter", "some/model") == "unknown"


def test_gemini_heuristic() -> None:
    assert classify("gemini", "gemini-2.5-flash") == "free"
    assert classify("gemini", "gemini-2.0-flash-lite") == "free"
    assert classify("gemini", "gemini-2.5-pro") == "paid"
    assert classify("gemini", "gemini-2.5-pro-exp-03-25") == "paid"


def test_fixed_tier_providers() -> None:
    assert classify("groq", "llama-3.3-70b-versatile") == "free"
    assert classify("freellmapi", "auto:smart") == "free"
    assert classify("custom", "llama3.1") == "free"
    assert classify("openai", "gpt-4o-mini") == "paid"
    assert classify("anthropic", "claude-3-5-haiku-20241022") == "paid"


def test_parse_openai_compatible_with_pricing() -> None:
    data = {
        "data": [
            {"id": "free-model", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "paid-model", "pricing": {"prompt": "0.1", "completion": "0.2"}},
        ]
    }
    models = _parse_openai_compatible(data, "openrouter", "trial")
    assert [m.id for m in models] == ["free-model", "paid-model"]
    assert [m.tier for m in models] == ["free", "paid"]


def test_parse_gemini_native_shape() -> None:
    data = {
        "models": [
            {
                "name": "models/gemini-2.0-flash",
                "displayName": "Gemini 2.0 Flash",
                "inputTokenLimit": 1048576,
            }
        ]
    }
    models = _parse_gemini(data)
    assert len(models) == 1
    assert models[0].id == "gemini-2.0-flash"
    assert models[0].name == "Gemini 2.0 Flash"
    assert models[0].tier == "free"
    assert models[0].context_length == 1048576


@pytest.mark.asyncio
async def test_no_base_url_returns_fallback() -> None:
    catalog = await fetch_models("groq", base_url="", api_key="")
    assert catalog.source == "fallback"
    assert catalog.models
    assert all(m.tier == "free" for m in catalog.models)


@pytest.mark.asyncio
async def test_unreachable_endpoint_returns_fallback() -> None:
    catalog = await fetch_models(
        "custom", base_url="http://127.0.0.1:1/v1", api_key="", timeout=1.0
    )
    assert catalog.source == "fallback"
    assert catalog.error


def test_fallback_catalog_contains_free_and_paid() -> None:
    catalog = _fallback_catalog("gemini", reason="offline")
    tiers = {m.tier for m in catalog.models}
    assert "free" in tiers
    assert "paid" in tiers
    assert catalog.source == "fallback"
    assert len(FALLBACK_MODELS["gemini"]) == len(catalog.models)


def test_catalog_as_dict_has_no_secret() -> None:
    catalog = ModelCatalog(
        models=[ModelInfo(id="m1", tier="free")], source="live"
    )
    payload = catalog.as_dict()
    assert payload["models"][0]["id"] == "m1"
    assert "key" not in str(payload).lower()
