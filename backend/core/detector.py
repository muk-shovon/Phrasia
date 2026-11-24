"""Local style pattern signal using our own pattern list."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

PATTERNS_PATH = Path(__file__).resolve().parent.parent / "engine" / "data" / "ai_patterns.json"
DISCLAIMER = (
    "Style signal, not proof of authorship. These highlights show common writing "
    "patterns and cannot determine who wrote the text."
)


@lru_cache(maxsize=1)
def _compiled() -> list[tuple[dict[str, Any], re.Pattern[str]]]:
    result: list[tuple[dict[str, Any], re.Pattern[str]]] = []
    for item in json.loads(PATTERNS_PATH.read_text(encoding="utf-8")):
        raw = str(item.get("pattern", ""))
        if not raw:
            continue
        if item.get("kind") == "regex":
            pattern = raw
        else:
            parts = [part.strip() for part in raw.split("|") if part.strip()]
            if not parts:
                continue
            pattern = r"(?<!\w)(?:" + "|".join(map(re.escape, parts)) + r")(?!\w)"
        try:
            result.append((item, re.compile(pattern, re.IGNORECASE | re.MULTILINE)))
        except re.error:
            continue
    return result


def find_matches(text: str) -> list[dict[str, Any]]:
    """Return pattern groups with highlight offsets into the source text."""
    groups: list[dict[str, Any]] = []
    for item, pattern in _compiled():
        matches = [
            {"start": int(match.start()), "end": int(match.end()), "text": match.group(0)}
            for match in pattern.finditer(text or "")
        ]
        if matches:
            groups.append({
                "id": item["id"],
                "name": item["name"],
                "hint": item["hint"],
                "weight": item["strength"],
                "count": len(matches),
                "matches": matches,
            })
    return groups


def analyze(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    patterns = find_matches(cleaned)
    return {
        "disclaimer": DISCLAIMER,
        "word_count": len(cleaned.split()),
        "total_matches": sum(int(item["count"]) for item in patterns),
        "patterns": patterns,
    }
