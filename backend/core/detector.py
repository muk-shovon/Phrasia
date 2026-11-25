"""Local style pattern signal using the shared skill scanner."""
from __future__ import annotations

from typing import Any

from backend.engine.skill import scan

DISCLAIMER = (
    "Style signal, not proof of authorship. These highlights show common writing "
    "patterns and cannot determine who wrote the text."
)


def find_matches(text: str) -> list[dict[str, Any]]:
    """Group gated tells by catalog entry, with highlight offsets into the source."""
    groups: dict[str, dict[str, Any]] = {}
    for tell in scan.scan(text or ""):
        entry = groups.get(tell["id"])
        if entry is None:
            entry = {
                "id": tell["id"],
                "name": tell["name"],
                "hint": tell["hint"],
                "weight": tell["strength"],
                "count": 0,
                "matches": [],
            }
            groups[tell["id"]] = entry
        entry["matches"].append({
            "start": int(tell["span"][0]),
            "end": int(tell["span"][1]),
            "text": tell["snippet"],
        })
        entry["count"] += 1
    return sorted(groups.values(), key=lambda item: (-int(item["count"]), str(item["name"])))


def analyze(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    patterns = find_matches(cleaned)
    return {
        "disclaimer": DISCLAIMER,
        "word_count": len(cleaned.split()),
        "total_matches": sum(int(item["count"]) for item in patterns),
        "patterns": patterns,
    }
