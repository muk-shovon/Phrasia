"""Post-generation quality checks (no detector, no scores)."""
from __future__ import annotations

import re
from typing import Any

from backend.core.ai_patterns import get_banned_words
from backend.core.sentence_align import Sentence, TaggedItem, _WORD_RE

_QUOTE_RE = re.compile(r'"[^"]*"|\'[^\']*\'|\u201c[^\u201d]*\u201d')


def _in_quote(text: str, start: int, end: int) -> bool:
    for m in _QUOTE_RE.finditer(text):
        if start >= m.start() and end <= m.end():
            return True
    return False


def banned_word_hits(sources: list[Sentence], items: list[TaggedItem]) -> dict[int, list[str]]:
    """Return source sentence indices -> banned words found in output but not in source."""
    src_map = {s.index: s.text for s in sources}
    hits: dict[int, list[str]] = {}
    banned = get_banned_words()
    # compile patterns
    pats: list[tuple[str, re.Pattern[str]]] = []
    for w in banned:
        w = str(w).strip()
        if not w: continue
        if w == "not only ... but also":
            pats.append((w, re.compile(r"\bnot\s+only\b.{0,80}\bbut\s+also\b", re.I)))
        else:
            pats.append((w, re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I)))
    for it in items:
        src_text = " ".join(src_map.get(i, "") for i in it.indices)
        src_low = src_text.lower()
        for label, rx in pats:
            m = rx.search(it.text)
            if not m: continue
            if _in_quote(it.text, m.start(), m.end()):
                continue
            # E6: replace even when in source; skip only quotes/code/protected spans
            for idx in it.indices:
                hits.setdefault(idx, [])
                if label not in hits[idx]:
                    hits[idx].append(label)
    return hits


def sentence_lengths(text: str) -> list[int]:
    # split by sentence endings roughly
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', text.strip()) if p.strip()]
    return [len(_WORD_RE.findall(p)) for p in parts] or [len(_WORD_RE.findall(text))]


def flat_rhythm_indices(sources: list[Sentence], items: list[TaggedItem]) -> list[int]:
    """Flag sentences in flat-rhythm runs (3 consecutive within +-20% or paragraph all narrow)."""
    # build per-output-sentence lengths in order
    lens: list[tuple[int, int]] = []  # (source_index_rep, length)
    src_map = {s.index: s.text for s in sources}
    for it in items:
        l = len(_WORD_RE.findall(it.text))
        rep = it.indices[0]
        lens.append((rep, l))
    flagged: set[int] = set()
    # three consecutive within +-20%
    for i in range(len(lens) - 2):
        a,b,c = lens[i][1], lens[i+1][1], lens[i+2][1]
        hi = max(a,b,c); lo = min(a,b,c)
        if lo > 0 and hi <= lo * 1.2:
            flagged.update([lens[i][0], lens[i+1][0], lens[i+2][0]])
    # paragraph all within narrow range - approximate by whole chunk if small
    if len(lens) >= 3:
        vals = [l for _,l in lens]
        if vals and max(vals) <= min(vals) * 1.25:
            flagged.update([idx for idx,_ in lens])
    # expand to all indices in merged items
    out: set[int] = set()
    for it in items:
        if any(i in flagged for i in it.indices):
            out.update(it.indices)
    return sorted(out)
