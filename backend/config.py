"""Runtime configuration. All values come from the environment or sane local defaults."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = Path(
    os.environ.get("PHRASIA_DATA_DIR", str(ROOT_DIR / "data"))
).expanduser().resolve()
DB_PATH = Path(
    os.environ.get("PHRASIA_DB_PATH", str(DATA_DIR / "phrasia.db"))
).expanduser().resolve()
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


PAID_MODELS_ENABLED = env_flag("PAID_MODELS_ENABLED", False)
PROVIDER_TIMEOUT_SECONDS = env_float("PROVIDER_TIMEOUT_SECONDS", 60.0)
MAX_INPUT_CHARS = env_int("MAX_INPUT_CHARS", 200_000)
CHUNK_CHARS = env_int("HUMANIZE_CHUNK_CHARS", 2_560)
MAX_UPLOAD_BYTES = env_int("MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
MAX_WORDS_PER_REQUEST = env_int("MAX_WORDS_PER_REQUEST", 1500)
