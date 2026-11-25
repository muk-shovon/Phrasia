"""Protected spans: URLs, emails, code, citations, quotes and measured numbers."""
from __future__ import annotations

import re
from dataclasses import dataclass

_URL = r"(?:https?|ftp)://[^\s<>\"']+|www\.[^\s<>\"']+"
_EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
_CITATION = r"\[\d+[\d,\s]*(?:;[\d,\s]*)*\]"
_MEASURE = (
    r"\b\d+(?:[.,]\d+)?\s*"
    r"(?:%|kg|km|cm|mm|ms|seconds?|minutes?|hours?|days?|weeks?|months?|years?|USD|\$|€|£|m|s)(?!\w)"
)
_QUOTE = r"\"[^\"\n]{3,}\"|“[^”\n]{3,}”"
_PATTERN = re.compile(
    r"```[\s\S]*?```|`[^`\n]+`|" + _URL + "|" + _EMAIL + "|" + _CITATION + "|" + _MEASURE + "|" + _QUOTE,
    re.IGNORECASE,
)
_PLACEHOLDER = "[PHRASIA_PROTECT_{}]"


@dataclass(frozen=True)
class Span:
    placeholder: str
    original: str


def extract(text: str) -> tuple[str, list[Span]]:
    """Replace protected spans with unique placeholders."""
    spans: list[Span] = []

    def replace(match: re.Match[str]) -> str:
        placeholder = _PLACEHOLDER.format(len(spans))
        spans.append(Span(placeholder, original=match.group(0)))
        return placeholder

    return _PATTERN.sub(replace, text or ""), spans


def restore(masked: str, spans: list[Span]) -> str | None:
    """Put every placeholder back exactly once, or return None."""
    result = masked
    for span in spans:
        if result.count(span.placeholder) != 1:
            return None
        result = result.replace(span.placeholder, span.original)
    if any(span.placeholder in result for span in spans):
        return None
    return result


def round_trip(text: str) -> bool:
    masked, spans = extract(text)
    return restore(masked, spans) == text
