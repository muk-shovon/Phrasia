"""Public humanize wrapper around the local deterministic engine."""
from __future__ import annotations

from typing import Any

from backend.config import MAX_WORDS_PER_REQUEST
from backend.engine import humanize as engine


def humanize(
    text: str,
    *,
    tone: str = "casual",
    strength: str = "medium",
    variation: int = 0,
    clean_invisible: bool = True,
) -> dict[str, Any]:
    """Rewrite text locally and return engine sentences plus API-shaped alignment."""
    if not text or not text.strip():
        raise ValueError("Text is empty.")
    words = len(text.split())
    if words > MAX_WORDS_PER_REQUEST:
        raise ValueError(
            f"This text is {words} words. The limit is {MAX_WORDS_PER_REQUEST} words per request."
        )

    result = engine.rewrite(
        text,
        tone=tone,
        strength=strength,
        variation=variation,
        preserve_formatting=True,
        clean_invisible=clean_invisible,
    )
    alignment: list[dict[str, Any]] = []
    for record in result["records"]:
        flags = [flag for flag in record["flags"] if flag in {"number", "meaning"}]
        alignment.append({
            "source_indices": record["source_ids"],
            "source_text": record["source"],
            "output_text": record["text"],
            "risk_flags": flags,
            "low_change": "low-change" in record["flags"],
            "restructured": record["restructured"],
            "unchanged": record["status"] == "unchanged",
            "similarity": record["similarity"],
        })
    return {
        "text": result["text"],
        "sentences": result["records"],
        "alignment": alignment,
        "summary": result["summary"],
    }
