"""Invisible-character cleanup and odd-space normalization."""
from __future__ import annotations

import re

INVISIBLE = ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff")
ODD_SPACES = (
    "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003", "\u2004",
    "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u202f",
    "\u205f", "\u3000",
)
_INVISIBLE_RE = re.compile("[" + "".join(map(re.escape, INVISIBLE)) + "]")
_ODD_RE = re.compile("[" + "".join(map(re.escape, ODD_SPACES)) + "]")


def normalize_spaces(text: str) -> str:
    """Map unusual spaces to plain spaces without touching line breaks."""
    return _ODD_RE.sub(" ", text)


def clean(text: str) -> str:
    """Remove invisible characters, then normalize unusual spaces."""
    return normalize_spaces(_INVISIBLE_RE.sub("", text or ""))
