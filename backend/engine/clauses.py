"""Clause segmentation by punctuation and closed-class markers."""
from __future__ import annotations

import re

from backend.engine.lexicon import COORDINATORS, SUBORDINATORS

_MARKERS = "|".join(sorted((COORDINATORS | SUBORDINATORS | {"however", "therefore"}), key=len, reverse=True))
_SPLIT = re.compile(r"(?<=,)\s+(?=(?:" + _MARKERS + r")\b)|(?<=;)\s+")
_WORD = re.compile(r"[A-Za-z0-9']+")


def split(sentence: str) -> list[str]:
    """Return clauses with their leading marker kept."""
    if not sentence or not sentence.strip():
        return []
    parts = [part.strip() for part in _SPLIT.split(sentence.strip()) if part.strip()]
    return parts or [sentence.strip()]


def markers(clause: str) -> list[str]:
    """Return coordinator/subordinator words found in a clause."""
    words = [word.lower() for word in _WORD.findall(clause)]
    return [word for word in words if word in COORDINATORS or word in SUBORDINATORS]
