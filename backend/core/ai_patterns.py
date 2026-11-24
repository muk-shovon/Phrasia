"""AI-writing pattern catalog.

Single source of truth loaded once from ai_patterns.json.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PATTERNS_PATH = Path(__file__).with_name("ai_patterns.json")


@lru_cache(maxsize=1)
def get_patterns() -> list[dict[str, Any]]:
    data = json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return data


@lru_cache(maxsize=1)
def _compiled() -> list[tuple[dict[str, Any], re.Pattern[str]]]:
    compiled: list[tuple[dict[str, Any], re.Pattern[str]]] = []
    for item in get_patterns():
        kind = str(item.get("type", "phrase"))
        raw = str(item.get("pattern", ""))
        if not raw:
            continue
        try:
            if kind == "regex":
                rx = re.compile(raw, re.IGNORECASE | re.MULTILINE)
            else:
                parts = [p.strip() for p in raw.split("|") if p.strip()]
                if not parts:
                    continue
                rx = re.compile(
                    r"(?<!\w)(" + "|".join(re.escape(p) for p in parts) + r")(?!\w)",
                    re.IGNORECASE,
                )
            compiled.append((item, rx))
        except re.error:
            continue
    return compiled


def strong_patterns(limit: int = 10) -> list[dict[str, Any]]:
    strong = [p for p in get_patterns() if p.get("weight") == "strong"]
    return strong[:limit]


def find_matches(text: str) -> list[dict[str, Any]]:
    """Return grouped pattern matches for detector display."""
    groups: list[dict[str, Any]] = []
    for item, rx in _compiled():
        spans: list[dict[str, int | str]] = []
        for m in rx.finditer(text):
            s = m.group(0)
            if not s:
                continue
            spans.append({"start": m.start(), "end": m.end(), "text": s[:120]})
            if len(spans) >= 50:
                break
        if not spans:
            continue
        groups.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "hint": item.get("hint"),
                "weight": item.get("weight"),
                "count": len(spans),
                "matches": spans,
            }
        )
    groups.sort(key=lambda g: (-int(g["count"]), str(g["name"])))
    return groups
