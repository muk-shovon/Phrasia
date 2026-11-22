"""Server-side credential store for user-supplied provider API keys.

Keys entered in the Settings page are persisted to a local JSON file that is
git-ignored (``.local/provider_settings.json`` by default) with best-effort
``0600`` permissions. Raw keys are never sent to the browser: the UI only ever
receives a masked preview plus the configuration *source* (saved / env / none).

Environment variables remain supported as a fallback so CI/Vercel deployments
can keep using secrets injected by the platform.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Optional

logger = logging.getLogger(__name__)

SETTINGS_PATH_ENV = "PHRASIA_SETTINGS_PATH"
LOCAL_DIR_ENV = "PHRASIA_LOCAL_DIR"
SETTINGS_FILENAME = "provider_settings.json"
SCHEMA_VERSION = 1

_LOCK = RLock()


def _empty_settings() -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "providers": {}, "preferences": {}}


def settings_path() -> Path:
    """Resolve the on-disk settings file.

    Priority: ``PHRASIA_SETTINGS_PATH`` → ``PHRASIA_LOCAL_DIR`` → repo ``.local/``.
    """
    override = os.environ.get(SETTINGS_PATH_ENV)
    if override:
        return Path(override).expanduser()
    base = os.environ.get(LOCAL_DIR_ENV)
    if base:
        return Path(base).expanduser() / SETTINGS_FILENAME
    project_root = Path(__file__).resolve().parent.parent
    return project_root / ".local" / SETTINGS_FILENAME


def _read() -> dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return _empty_settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read provider settings (%s); starting empty", type(exc).__name__)
        return _empty_settings()
    if not isinstance(raw, dict):
        return _empty_settings()
    data = _empty_settings()
    providers = raw.get("providers")
    if isinstance(providers, dict):
        data["providers"] = {
            str(k): v for k, v in providers.items() if isinstance(v, dict)
        }
    prefs = raw.get("preferences")
    if isinstance(prefs, dict):
        data["preferences"] = {str(k): v for k, v in prefs.items()}
    return data


def _write(data: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".provider_settings.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - Windows ACLs ignore POSIX modes
        pass


def get_settings() -> dict[str, Any]:
    """Return a deep copy of the stored settings."""
    with _LOCK:
        return copy.deepcopy(_read())


def get_provider(provider_id: str) -> dict[str, Any]:
    with _LOCK:
        return copy.deepcopy(_read()["providers"].get(provider_id, {}))


def update_provider(
    provider_id: str,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    display_name: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> dict[str, Any]:
    """Persist provider overrides.

    ``None`` means "leave unchanged". An empty string for ``model``/``base_url``
    removes the override; an empty ``api_key`` is ignored (use
    :func:`clear_api_key` to remove a saved key).
    """
    with _LOCK:
        data = _read()
        record = data["providers"].get(provider_id, {})

        if api_key is not None and api_key.strip():
            record["api_key"] = api_key.strip()
        if model is not None:
            if model.strip():
                record["model"] = model.strip()
            else:
                record.pop("model", None)
        if base_url is not None:
            if base_url.strip():
                record["base_url"] = base_url.strip().rstrip("/")
            else:
                record.pop("base_url", None)
        if display_name is not None:
            if display_name.strip():
                record["display_name"] = display_name.strip()
            else:
                record.pop("display_name", None)
        if enabled is not None:
            record["enabled"] = bool(enabled)

        if record:
            data["providers"][provider_id] = record
        else:
            data["providers"].pop(provider_id, None)
        _write(data)
        return copy.deepcopy(record)


def clear_api_key(provider_id: str) -> None:
    """Remove only the saved key, keeping model/base-url overrides."""
    with _LOCK:
        data = _read()
        record = data["providers"].get(provider_id)
        if not record:
            return
        record.pop("api_key", None)
        if not record:
            data["providers"].pop(provider_id, None)
        _write(data)


def remove_provider(provider_id: str) -> None:
    with _LOCK:
        data = _read()
        if data["providers"].pop(provider_id, None) is not None:
            _write(data)


def set_preferences(**values: Any) -> None:
    with _LOCK:
        data = _read()
        prefs = data["preferences"]
        for key, value in values.items():
            if value in (None, ""):
                prefs.pop(key, None)
            else:
                prefs[key] = value
        _write(data)


def get_preference(key: str, default: Any = None) -> Any:
    with _LOCK:
        return _read()["preferences"].get(key, default)


def resolve_secret(provider_id: str, env_var: str, default: str = "") -> str:
    """Saved key wins over the environment; environment wins over ``default``."""
    saved = get_provider(provider_id).get("api_key") or ""
    return saved or os.environ.get(env_var, "") or default


def resolve_setting(
    provider_id: str,
    field: str,
    env_var: Optional[str] = None,
    default: str = "",
) -> str:
    saved = get_provider(provider_id).get(field) or ""
    if saved:
        return saved
    if env_var:
        return os.environ.get(env_var) or default
    return default


def secret_source(provider_id: str, env_var: str) -> str:
    """Return ``"saved"``, ``"env"`` or ``"none"`` for UI badges."""
    if get_provider(provider_id).get("api_key"):
        return "saved"
    if os.environ.get(env_var):
        return "env"
    return "none"


def is_configured(provider_id: str, env_var: str) -> bool:
    return bool(resolve_secret(provider_id, env_var))


def mask_secret(secret: str) -> str:
    """Mask a key so it can be displayed safely (last 4 chars only)."""
    value = (secret or "").strip()
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"••••{value[-4:]}"


def provider_summary(provider_id: str, env_var: str) -> dict[str, Any]:
    """Safe, non-secret view of a provider for UI consumption."""
    record = get_provider(provider_id)
    return {
        "provider_id": provider_id,
        "source": secret_source(provider_id, env_var),
        "masked": mask_secret(resolve_secret(provider_id, env_var)),
        "model": record.get("model", ""),
        "base_url": record.get("base_url", ""),
    }
