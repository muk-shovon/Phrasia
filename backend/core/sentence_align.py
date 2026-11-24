"""Sentence-aligned humanization helpers."""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any

from backend.core.protected_spans import extract_spans

_ABBREV = {"e.g", "i.e", "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc", "no", "fig", "al"}
_SENT_END = re.compile(r'([.!??]["\'??)\]]*)\s+')
_TAG_RE = re.compile(r"^\s*\[(S\d+(?:\+S\d+)*)\]\s*(.*)$", re.IGNORECASE)
_NUM_RE = re.compile(r"\d+(?:[\.,]\d+)?")
_WORD_RE = re.compile(r"\S+")
_HEDGE_RE = re.compile(r"\b(may|might|can|could|should|must|would|always|usually|often|rarely|never|not|no|n't)\b", re.I)


@dataclass
class Sentence:
    index: int  # 1-based
    text: str


@dataclass
class TaggedItem:
    indices: list[int]
    text: str


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, respecting common abbreviations and decimals."""
    t = (text or "").strip()
    if not t:
        return []
    # mask protected spans to avoid splitting inside them
    masked, spans = extract_spans(t)
    parts: list[str] = []
    start = 0
    for m in _SENT_END.finditer(masked):
        end = m.end()
        chunk = masked[start:end]
        # check abbreviation before punctuation
        before = masked[:m.start(1)].rstrip()
        word = re.search(r"([A-Za-z.]+)$", before)
        if word:
            w = word.group(1).lower().rstrip('.')
            if w in _ABBREV or (len(w) == 1 and w.isalpha()):
                continue
        # decimal like 3.14
        if re.search(r"\d$", before) and re.match(r"\d", masked[m.end(1):m.end(1)+1]):
            continue
        parts.append(chunk)
        start = end
    if start < len(masked):
        parts.append(masked[start:])
    # unmask spans by restoring - simple: map back through original? easier to split original by indices
    # Better: use masked split positions to cut original. We'll do a simple approach: split original by sentence-end regex and merge same count.
    # Fallback: split original with same logic but no span masking complications for most cases.
    orig_parts = _split_plain(t)
    return orig_parts if orig_parts else [t]


def _split_plain(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    for m in _SENT_END.finditer(text):
        end = m.end()
        before = text[:m.start(1)].rstrip()
        word = re.search(r"([A-Za-z.]+)$", before)
        if word:
            w = word.group(1).lower().rstrip('.')
            if w in _ABBREV or (len(w) == 1 and w.isalpha()):
                continue
        if re.search(r"\d$", before) and re.match(r"\d", text[m.end(1):m.end(1)+1]):
            continue
        parts.append(text[start:end].strip())
        start = end
    if start < len(text):
        tail = text[start:].strip()
        if tail:
            parts.append(tail)
    return [p for p in parts if p]


def tag_sentences(text: str) -> tuple[list[Sentence], str]:
    sents = [Sentence(i + 1, s) for i, s in enumerate(split_sentences(text))]
    tagged = "\n".join(f"[S{s.index}] {s.text}" for s in sents)
    return sents, tagged


def parse_tagged_output(output: str) -> list[TaggedItem]:
    items: list[TaggedItem] = []
    for raw in (output or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _TAG_RE.match(line)
        if not m:
            # try to find tag anywhere in line start
            m2 = re.match(r"^\s*\[(S\d+(?:\+S\d+)*)\]\s*(.*)$", line, re.I)
            if not m2:
                return []
            m = m2
        idxs = [int(x[1:]) for x in m.group(1).upper().split("+") if x.upper().startswith("S")]
        txt = m.group(2).strip()
        if not idxs or not txt:
            return []
        items.append(TaggedItem(indices=idxs, text=txt))
    return items


def validate_tagged(items: list[TaggedItem], n: int) -> tuple[bool, str]:
    if not items:
        return False, "no tagged items"
    seen: list[int] = []
    for it in items:
        if any(i < 1 or i > n for i in it.indices):
            return False, "tag out of range"
        seen.extend(it.indices)
    if sorted(seen) != list(range(1, n + 1)):
        return False, "missing or duplicated sentence tags"
    # ordering: first index of items must be non-decreasing in coverage order
    flat = []
    for it in items:
        flat.extend(it.indices)
    if flat != sorted(flat):
        # allow merged [S1+S2] but overall coverage must be in order
        pass
    # ensure every index appears once
    if len(seen) != len(set(seen)):
        return False, "duplicated sentence tags"
    # check in order
    expected = 1
    for it in items:
        for idx in it.indices:
            if idx != expected:
                return False, "tags out of order"
            expected += 1
    return True, "ok"


def strip_tags(items: list[TaggedItem]) -> str:
    return " ".join(it.text.strip() for it in items if it.text.strip()).strip()


def word_set_overlap(a: str, b: str) -> float:
    aw = {w.lower().strip(".,;:!?\"'()[]{}") for w in _WORD_RE.findall(a)}
    bw = {w.lower().strip(".,;:!?\"'()[]{}") for w in _WORD_RE.findall(b)}
    aw.discard(""); bw.discard("")
    if not aw or not bw:
        return 0.0
    return len(aw & bw) / max(len(aw | bw), 1)


def structure_similarity(a: str, b: str) -> float:
    # combine sequence ratio and word-set overlap; high means too similar
    seq = difflib.SequenceMatcher(None, a.lower(), b.lower(), autojunk=False).ratio()
    ov = word_set_overlap(a, b)
    return max(seq, ov)


def low_change_indices(sources: list[Sentence], items: list[TaggedItem], threshold: float = 0.60) -> list[int]:
    src = {s.index: s.text for s in sources}
    low: list[int] = []
    for it in items:
        # compare against concatenated source for merged/split
        src_text = " ".join(src.get(i, "") for i in it.indices).strip()
        sim = structure_similarity(src_text, it.text)
        if sim > threshold:
            low.extend(it.indices)
    return sorted(set(low))


def meaning_flags(source_text: str, rewritten_text: str) -> list[str]:
    flags: list[str] = []
    s_nums = _NUM_RE.findall(source_text)
    r_nums = _NUM_RE.findall(rewritten_text)
    if s_nums != r_nums:
        flags.append("number")
    s_hedges = [h.lower() for h in _HEDGE_RE.findall(source_text)]
    r_hedges = [h.lower() for h in _HEDGE_RE.findall(rewritten_text)]
    # flag if a hedge/modal/negation present in source is lost
    for h in s_hedges:
        if h not in r_hedges:
            flags.append("meaning")
            break
    return sorted(set(flags))


def build_alignment(sources: list[Sentence], items: list[TaggedItem], low_indices: set[int] | None = None) -> list[dict[str, Any]]:
    src = {s.index: s.text for s in sources}
    low = low_indices or set()
    out = []
    for it in items:
        src_text = " ".join(src.get(i, "") for i in it.indices).strip()
        flags = meaning_flags(src_text, it.text)
        sim = structure_similarity(src_text, it.text)
        out.append({
            "source_indices": it.indices,
            "source_text": src_text,
            "output_text": it.text,
            "risk_flags": flags,
            "low_change": any(i in low for i in it.indices) or sim > 0.60,
            "similarity": round(sim, 3),
        })
    return out
