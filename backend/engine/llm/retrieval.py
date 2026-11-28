"""Few-shot example retrieval."""
from __future__ import annotations

import re
from typing import Any

_WORD = re.compile(r"[a-z][a-z']{2,}")
_STOP = {
    "about", "after", "again", "also", "because", "been", "before", "being",
    "between", "could", "does", "each", "from", "have", "into", "just", "more",
    "most", "much", "only", "other", "over", "same", "should", "some", "such",
    "than", "that", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "under", "very", "were", "what", "when", "where",
    "which", "while", "will", "with", "would", "your",
}


def tokens(text: str) -> set[str]:
    return {
        word for word in _WORD.findall((text or "").lower())
        if word not in _STOP
    }


def score_row(row: dict[str, Any], query: set[str]) -> float:
    if not query:
        return float(row.get("rating", 0))
    source = tokens(str(row.get("source_text", "")))
    overlap = len(query & source) / max(len(query | source), 1)
    length_gap = abs(len(str(row.get("source_text", ""))) - len(str(row.get("rewritten_text", ""))))
    closeness = 1.0 / (1.0 + length_gap / 400.0)
    rating = float(row.get("rating", 0)) * 0.05
    return overlap * 2.0 + closeness * 0.3 + rating


def retrieve(
    tone: str, strength: str, query: str, limit: int = 4, operation: str | None = None
) -> list[dict[str, Any]]:
    from backend.db import repository

    try:
        rows = repository.list_example_pairs(
            tone=tone, strength=strength, operation=operation, limit=200
        )
    except Exception:
        return []
    if not rows:
        return []
    wanted = tokens(query)
    ranked = sorted(rows, key=lambda row: score_row(row, wanted), reverse=True)
    return ranked[:limit]
