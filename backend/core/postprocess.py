"""Small post-generation cleanup. Default OFF.

Nothing here is enabled unless the owner passes the matching option. The
functions skip protected spans so URLs, emails, code blocks, citations and
quoted text are left exactly as the model wrote them.
"""
from __future__ import annotations

from backend.core import protected_spans


def _no_excess_newlines(text: str) -> str:
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def strip_trailing_spaces(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.split("\n"))


def remove_em_dashes(text: str) -> str:
    """Replace em dashes (and en dashes between words) with lighter punctuation."""
    result = text.replace(" — ", ", ").replace("—", ",")
    result = result.replace(" – ", ", ").replace("–", ",")
    return result


def apply_optional_edits(
    text: str,
    *,
    remove_em_dashes: bool = False,
    clean_whitespace: bool = True,
) -> str:
    redacted, spans = protected_spans.extract_spans(text)
    result = redacted
    if remove_em_dashes:
        result = remove_em_dashes(result)
    if clean_whitespace:
        result = strip_trailing_spaces(_no_excess_newlines(result))
    restored = protected_spans.restore_spans(result, spans)
    return text if restored is None else restored
