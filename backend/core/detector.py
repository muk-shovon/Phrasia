"""Local writing-style signal using ai_patterns.json.

This reports pattern matches as a style signal, not proof of authorship.
"""
from __future__ import annotations

from typing import Any

from backend.core.ai_patterns import find_matches

DISCLAIMER = (
    "Style signal, not proof of authorship. These highlights show common writing "
    "patterns and cannot determine who wrote the text."
)


def analyze(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    words = cleaned.split()
    patterns = find_matches(cleaned)
    total_matches = sum(int(p.get("count", 0)) for p in patterns)
    return {
        "disclaimer": DISCLAIMER,
        "word_count": len(words),
        "total_matches": total_matches,
        "patterns": patterns,
    }
