"""Tone presets loaded from data/tones.json."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent / "data" / "tones.json"


@lru_cache(maxsize=1)
def presets() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def normalise(tone: str | None) -> str:
    value = (tone or "").strip().lower()
    return value if value in presets()["tones"] else "casual"


def preset(tone: str | None) -> dict[str, Any]:
    return presets()["tones"][normalise(tone)]


def contraction_tones() -> set[str]:
    return {name for name, item in presets()["tones"].items() if item["contractions"]}
