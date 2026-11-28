"""Online provider settings and local key storage.

Keys are read from the process environment first and then from a private
``.env`` file inside the data directory. They are never written to logs,
database rows or API responses.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"
SECRETS_PATH = DATA_DIR / ".env"

DEFAULT_ORDER = ("groq", "cerebras", "gemini", "mistral", "openrouter", "together")


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    env_keys: tuple[str, ...]
    base_url: str
    default_model: str
    protocol: str
    docs_url: str
    note: str


PROVIDERS: dict[str, ProviderSpec] = {
    "groq": ProviderSpec(
        id="groq",
        label="Groq",
        env_keys=("GROQ_API_KEY",),
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        protocol="openai",
        docs_url="https://console.groq.com/keys",
        note="Fast hosted inference with a free tier.",
    ),
    "cerebras": ProviderSpec(
        id="cerebras",
        label="Cerebras",
        env_keys=("CEREBRAS_API_KEY",),
        base_url="https://api.cerebras.ai/v1",
        default_model="llama-3.3-70b",
        protocol="openai",
        docs_url="https://cloud.cerebras.ai",
        note="Low-latency hosted inference with a free tier.",
    ),
    "gemini": ProviderSpec(
        id="gemini",
        label="Google Gemini",
        env_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-2.0-flash",
        protocol="gemini",
        docs_url="https://aistudio.google.com/app/apikey",
        note="Free tier through Google AI Studio.",
    ),
    "mistral": ProviderSpec(
        id="mistral",
        label="Mistral",
        env_keys=("MISTRAL_API_KEY",),
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
        protocol="openai",
        docs_url="https://console.mistral.ai/api-keys",
        note="Hosted models with a free experimental tier.",
    ),
    "openrouter": ProviderSpec(
        id="openrouter",
        label="OpenRouter",
        env_keys=("OPENROUTER_API_KEY",),
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        protocol="openai",
        docs_url="https://openrouter.ai/keys",
        note="Free model routing; model names change over time.",
    ),
    "together": ProviderSpec(
        id="together",
        label="Together AI",
        env_keys=("TOGETHER_API_KEY",),
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        protocol="openai",
        docs_url="https://api.together.ai/settings/api-keys",
        note="Hosted open models with a free endpoint.",
    ),
}

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "provider_order": list(DEFAULT_ORDER),
    "models": {},
    "preferred_provider": "auto",
    "offline_fallback": True,
    "temperature": 0.7,
    "max_tokens": 2048,
    "timeout_seconds": 60,
    "target_density": 1.0,
}


def _as_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _as_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def load_settings() -> dict[str, Any]:
    """Return validated settings, falling back to defaults for bad input."""
    stored: dict[str, Any] = {}
    try:
        if SETTINGS_PATH.is_file():
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                stored = raw
    except (OSError, ValueError):
        stored = {}

    order = [
        str(item) for item in stored.get("provider_order", DEFAULTS["provider_order"])
        if str(item) in PROVIDERS
    ]
    order.extend(item for item in DEFAULT_ORDER if item not in order)
    models = {
        str(key): str(value)[:120]
        for key, value in (stored.get("models") or {}).items()
        if str(key) in PROVIDERS and str(value).strip()
    }
    preferred = str(stored.get("preferred_provider", "auto"))
    if preferred != "auto" and preferred not in PROVIDERS:
        preferred = "auto"
    return {
        "enabled": _as_bool(stored.get("enabled"), bool(DEFAULTS["enabled"])),
        "provider_order": order,
        "models": models,
        "preferred_provider": preferred,
        "offline_fallback": _as_bool(
            stored.get("offline_fallback"), bool(DEFAULTS["offline_fallback"])
        ),
        "temperature": _as_float(stored.get("temperature"), 0.7, 0.0, 1.5),
        "max_tokens": _as_int(stored.get("max_tokens"), 2048, 256, 8192),
        "timeout_seconds": _as_int(stored.get("timeout_seconds"), 60, 5, 180),
        "target_density": _as_float(stored.get("target_density"), 1.0, 0.0, 10.0),
    }


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    merged = {**current, **{key: value for key, value in patch.items() if value is not None}}
    if "provider_order" in patch and isinstance(patch["provider_order"], list):
        merged["provider_order"] = [
            str(item) for item in patch["provider_order"] if str(item) in PROVIDERS
        ]
    if "models" in patch and isinstance(patch["models"], dict):
        merged["models"] = {
            str(key): str(value)[:120]
            for key, value in patch["models"].items()
            if str(key) in PROVIDERS and str(value).strip()
        }
    if "preferred_provider" in patch:
        value = str(patch["preferred_provider"])
        merged["preferred_provider"] = value if value in PROVIDERS or value == "auto" else "auto"
    merged["enabled"] = bool(merged.get("enabled", True))
    merged["offline_fallback"] = bool(merged.get("offline_fallback", True))
    merged["temperature"] = _as_float(merged.get("temperature"), 0.7, 0.0, 1.5)
    merged["max_tokens"] = _as_int(merged.get("max_tokens"), 2048, 256, 8192)
    merged["timeout_seconds"] = _as_int(merged.get("timeout_seconds"), 60, 5, 180)
    merged["target_density"] = _as_float(merged.get("target_density"), 1.0, 0.0, 10.0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return merged


def _read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        if not SECRETS_PATH.is_file():
            return values
        for line in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                values[key] = value
    except OSError:
        return {}
    return values


def _write_env_file(values: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Phrasia provider keys. Local only. Do not commit this file."]
    for key in sorted(values):
        value = values[key]
        if not value:
            continue
        if any(character.isspace() for character in value) or "#" in value:
            value = json.dumps(value)
        lines.append(f"{key}={value}")
    SECRETS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(SECRETS_PATH, 0o600)
    except OSError:
        pass


def api_key(provider: str) -> str:
    spec = PROVIDERS.get(provider)
    if spec is None:
        return ""
    for name in spec.env_keys:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    values = _read_env_file()
    for name in spec.env_keys:
        value = values.get(name, "").strip()
        if value:
            return value
    return ""


def key_source(provider: str) -> str | None:
    spec = PROVIDERS.get(provider)
    if spec is None:
        return None
    for name in spec.env_keys:
        if os.environ.get(name, "").strip():
            return "environment"
    values = _read_env_file()
    for name in spec.env_keys:
        if values.get(name, "").strip():
            return "file"
    return None


def save_key(provider: str, key: str) -> None:
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise ValueError("Unknown provider.")
    value = (key or "").strip()
    if not value:
        raise ValueError("The key is empty.")
    values = _read_env_file()
    for name in spec.env_keys:
        values.pop(name, None)
    values[spec.env_keys[0]] = value
    _write_env_file(values)


def delete_key(provider: str) -> None:
    spec = PROVIDERS.get(provider)
    if spec is None:
        raise ValueError("Unknown provider.")
    values = _read_env_file()
    for name in spec.env_keys:
        values.pop(name, None)
    _write_env_file(values)


def model_for(provider: str) -> str:
    settings = load_settings()
    return str(settings["models"].get(provider) or PROVIDERS[provider].default_model)


def configured_providers() -> list[str]:
    return [provider for provider in PROVIDERS if api_key(provider)]


def provider_order(preferred: str = "auto") -> list[str]:
    settings = load_settings()
    configured = set(configured_providers())
    order = [provider for provider in settings["provider_order"] if provider in configured]
    if preferred not in {"", "auto"}:
        if preferred in configured:
            order = [preferred] + [provider for provider in order if provider != preferred]
        elif preferred in PROVIDERS:
            order = [preferred] + order
    elif settings["preferred_provider"] != "auto":
        chosen = settings["preferred_provider"]
        if chosen in configured:
            order = [chosen] + [provider for provider in order if provider != chosen]
    return order


def provider_catalog() -> list[dict[str, Any]]:
    settings = load_settings()
    result: list[dict[str, Any]] = []
    for provider, spec in PROVIDERS.items():
        source = key_source(provider)
        result.append({
            "id": spec.id,
            "label": spec.label,
            "note": spec.note,
            "docs_url": spec.docs_url,
            "env_keys": list(spec.env_keys),
            "protocol": spec.protocol,
            "base_url": spec.base_url,
            "default_model": spec.default_model,
            "model": str(settings["models"].get(provider) or spec.default_model),
            "configured": source is not None,
            "key_source": source,
        })
    return result


def public_settings() -> dict[str, Any]:
    settings = load_settings()
    return {
        **settings,
        "providers": provider_catalog(),
        "config_path": str(SETTINGS_PATH),
        "secrets_path": str(SECRETS_PATH),
    }


def resolve_paths() -> tuple[Path, Path]:
    return SETTINGS_PATH, SECRETS_PATH
