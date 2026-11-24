"""Sentence splitting with abbreviation, decimal, initial and ellipsis handling."""
from __future__ import annotations

import re

_BOUNDARY = re.compile(r"[.!?…]+[\"'”’)\]]*\s+")
_ABBREVIATIONS = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs", "etc", "no",
    "fig", "al", "e.g", "i.e", "u.s", "u.k", "a.m", "p.m",
}
_WORD_BEFORE = re.compile(r"([A-Za-z]+(?:\.[A-Za-z]+)*\.?)$")


def split(text: str) -> list[str]:
    """Return sentences, each keeping the whitespace that followed it."""
    source = text or ""
    pieces: list[str] = []
    start = 0
    for match in _BOUNDARY.finditer(source):
        before = source[:match.start()]
        token = _WORD_BEFORE.search(before)
        if token:
            value = token.group(1).lower()
            bare = value.rstrip(".")
            if bare in _ABBREVIATIONS or (len(bare) == 1 and bare.isalpha()):
                continue
        end = match.end()
        if end > start:
            pieces.append(source[start:end])
            start = end
    if start < len(source):
        pieces.append(source[start:])
    return [piece for piece in pieces if piece]


def texts(text: str) -> list[str]:
    """Sentence contents without trailing whitespace."""
    return [piece.strip() for piece in split(text) if piece.strip()]
