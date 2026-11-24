"""Runtime configuration. Local defaults, no environment secrets."""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PHRASIA_DATA_DIR", str(ROOT_DIR / "data"))).expanduser().resolve()
DB_PATH = Path(os.environ.get("PHRASIA_DB_PATH", str(DATA_DIR / "phrasia.db"))).expanduser().resolve()
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

MAX_INPUT_CHARS = 200_000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_WORDS_PER_REQUEST = 1500
