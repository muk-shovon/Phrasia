"""Mask non-rewritable spans before they go to a provider.

URLs, emails, code blocks, citations and quoted passages are replaced by
placeholders, the model rewrites the remaining text, and restoration checks
that every placeholder came back exactly once. A chunk whose restoration is
incomplete or has duplicates is retried.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FENCED_CODE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"\b(?:https?|ftp)://[^\s<>\"']+|www\.[^\s<>\"']+")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_CITATION = re.compile(r"\b\[\d+[\d,\s]*(?:;[\d,\s]*)*\]")
_QUOTED = re.compile(r'"[^"\n]{25,}"')


@dataclass(frozen=True)
class Span:
    placeholder: str
    original: str


_PATTERNS: tuple[re.Pattern[str], ...] = (
    _FENCED_CODE,
    _INLINE_CODE,
    _URL,
    _EMAIL,
    _CITATION,
    _QUOTED,
)


def extract_spans(text: str) -> tuple[str, list[Span]]:
    """Return ``text`` with every protected span replaced by a placeholder."""
    spans: list[Span] = []
    working = text

    for pattern in _PATTERNS:
        def replace(match: re.Match[str], working: str = working) -> str:
            placeholder = f"[PHRASIA_SPAN_{len(spans)}]"
            spans.append(Span(placeholder=placeholder, original=match.group(0)))
            return placeholder

        working = pattern.sub(replace, working)

    return working, spans


def restore_spans(redacted: str, spans: list[Span]) -> str | None:
    """Put every placeholder back.

    Returns None when restoration is not exact: every placeholder must come
    back exactly once, so both "missing" and "still present" count as a retry.
    """
    result = redacted
    for span in spans:
        if result.count(span.placeholder) == 0:
            return None
        result = result.replace(span.placeholder, span.original, 1)

    if any(span.placeholder in result for span in spans):
        return None
    return result
