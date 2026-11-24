"""Input hygiene helpers.

These cleanups are optional readability/normalization aids. They are never
framed as detection bypass.
"""
from __future__ import annotations

import re

# Zero-width/invisible characters to remove by default.
_INVISIBLE = {
    "\u200b",  # ZERO WIDTH SPACE
    "\u200c",  # ZERO WIDTH NON-JOINER
    "\u200d",  # ZERO WIDTH JOINER
    "\u2060",  # WORD JOINER
    "\ufeff",  # ZERO WIDTH NO-BREAK SPACE / BOM
}

# Unusual spaces normalized to regular space.
_ODD_SPACES = {
    "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003", "\u2004",
    "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u202f",
    "\u205f", "\u3000",
}

_INVISIBLE_RE = re.compile("[" + "".join(re.escape(c) for c in sorted(_INVISIBLE)) + "]")
_ODD_SPACE_RE = re.compile("[" + "".join(re.escape(c) for c in sorted(_ODD_SPACES)) + "]")


def clean_invisible_characters(text: str) -> str:
    """Remove invisible characters and normalize odd spaces."""
    if not text:
        return text
    cleaned = _INVISIBLE_RE.sub("", text)
    cleaned = _ODD_SPACE_RE.sub(" ", cleaned)
    return cleaned
