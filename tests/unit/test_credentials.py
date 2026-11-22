"""Tests for the server-side provider credential store."""
from __future__ import annotations

import json

import pytest

from providers import credentials

ENV_VAR = "TEST_PROVIDER_KEY"


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv(credentials.SETTINGS_PATH_ENV, str(tmp_path / "settings.json"))
    monkeypatch.delenv(ENV_VAR, raising=False)
    yield
    monkeypatch.delenv(ENV_VAR, raising=False)


def test_saved_key_wins_over_environment(monkeypatch) -> None:
    monkeypatch.setenv(ENV_VAR, "env-key-123456")
    assert credentials.resolve_secret("demo", ENV_VAR) == "env-key-123456"
    assert credentials.secret_source("demo", ENV_VAR) == "env"

    credentials.update_provider("demo", api_key="saved-key-abcdef")

    assert credentials.resolve_secret("demo", ENV_VAR) == "saved-key-abcdef"
    assert credentials.secret_source("demo", ENV_VAR) == "saved"


def test_clear_key_falls_back_to_environment(monkeypatch) -> None:
    monkeypatch.setenv(ENV_VAR, "env-key-123456")
    credentials.update_provider("demo", api_key="saved-key-abcdef")

    credentials.clear_api_key("demo")

    assert credentials.resolve_secret("demo", ENV_VAR) == "env-key-123456"
    assert credentials.secret_source("demo", ENV_VAR) == "env"


def test_mask_secret_never_exposes_full_key() -> None:
    masked = credentials.mask_secret("sk-1234567890abcdef")
    assert masked.endswith("cdef")
    assert "1234567890" not in masked
    assert credentials.mask_secret("") == ""
    assert credentials.mask_secret("short") == "••••••••"


def test_custom_endpoint_roundtrip() -> None:
    credentials.update_provider(
        "custom",
        api_key="local-key",
        base_url="http://127.0.0.1:11434/v1/",
        model="llama3.1",
        display_name="My Ollama",
    )
    record = credentials.get_provider("custom")

    assert record["api_key"] == "local-key"
    assert record["base_url"] == "http://127.0.0.1:11434/v1"  # trailing slash removed
    assert record["model"] == "llama3.1"
    assert record["display_name"] == "My Ollama"
    assert credentials.resolve_setting("custom", "model") == "llama3.1"


def test_empty_model_removes_override() -> None:
    credentials.update_provider("custom", model="llama3.1")
    credentials.update_provider("custom", model="")
    assert "model" not in credentials.get_provider("custom")


def test_preferences_roundtrip() -> None:
    credentials.set_preferences(preferred_provider="groq", routing_mode="hybrid")
    assert credentials.get_preference("preferred_provider") == "groq"
    assert credentials.get_preference("routing_mode") == "hybrid"

    credentials.set_preferences(preferred_provider="")
    assert credentials.get_preference("preferred_provider", "auto") == "auto"


def test_corrupt_file_does_not_raise(tmp_path, monkeypatch) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv(credentials.SETTINGS_PATH_ENV, str(path))

    assert credentials.get_settings()["providers"] == {}
    credentials.update_provider("demo", api_key="k")
    assert json.loads(path.read_text(encoding="utf-8"))["providers"]["demo"]["api_key"] == "k"


def test_remove_provider_deletes_record() -> None:
    credentials.update_provider("danger", api_key="secret-key-value")
    credentials.remove_provider("danger")
    assert credentials.get_provider("danger") == {}
