"""Rhythm planner: short, medium and long sentences without flat runs."""
from __future__ import annotations

import re
from typing import Any

_TARGETS = {"short": 5, "medium": 11, "long": 20}
_WORD = re.compile(r"\S+")


def word_count(sentence: str) -> int:
    return len(_WORD.findall(sentence or ""))


def target_lengths(count: int) -> list[str]:
    """Assign a length category to each sentence in a paragraph."""
    categories: list[str] = []
    for index in range(count):
        allowed = list(_TARGETS)
        if len(categories) >= 2 and categories[-1] == categories[-2]:
            allowed = [item for item in allowed if item != categories[-1]]
        categories.append(allowed[index % len(allowed)])
    return categories


def targets(sentences: list[str]) -> list[int]:
    categories = target_lengths(len(sentences))
    return [_TARGETS[category] for category in categories]


def is_flat_run(lengths: list[int]) -> bool:
    """Three consecutive lengths within ±20% of each other."""
    for index in range(len(lengths) - 2):
        window = lengths[index:index + 3]
        low, high = min(window), max(window)
        if low > 0 and high <= low * 1.2:
            return True
    return False


def rhythm_fit(length: int, target: int) -> float:
    if target <= 0:
        return 0.0
    return round(max(0.0, 1.0 - abs(length - target) / target), 3)


def report(sentences: list[str]) -> dict[str, Any]:
    lengths = [word_count(item) for item in sentences]
    return {
        "lengths": lengths,
        "targets": targets(sentences),
        "flat_run": is_flat_run(lengths),
    }
