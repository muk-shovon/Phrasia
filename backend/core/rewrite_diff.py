"""Diff and style-check helpers for humanize output."""
from __future__ import annotations

import difflib
import re
from typing import Any

from backend.core.ai_patterns import find_matches

_WORD_RE = re.compile(r"\S+")
_NUM_RE = re.compile(r"\d+(?:[\.,]\d+)?")


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text or "")


def _has_number_change(a: str, b: str) -> bool:
    return _NUM_RE.findall(a) != _NUM_RE.findall(b)


def _risk(a: str, b: str) -> str:
    if not a.strip() or not b.strip():
        # pure insert/delete - can be meaning risk if substantive
        t = (a or b)
        if _NUM_RE.search(t):
            return "number"
        return "meaning" if len(_tokens(t)) > 0 else "none"
    if _has_number_change(a, b):
        return "number"
    # substantive word replacement -> meaning risk
    aw = [w.lower().strip(".,;:!?\"'()[]{}") for w in _tokens(a)]
    bw = [w.lower().strip(".,;:!?\"'()[]{}") for w in _tokens(b)]
    if aw == bw:
        return "none"
    return "meaning"


def diff_segments(original: str, rewritten: str) -> list[dict[str, Any]]:
    a = _tokens(original)
    b = _tokens(rewritten)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    raw: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            txt = " ".join(a[i1:i2])
            if txt:
                raw.append({"type": "equal", "text": txt, "original": txt, "risk": "none"})
        else:
            o = " ".join(a[i1:i2])
            r = " ".join(b[j1:j2])
            raw.append({"type": "changed", "original": o, "rewritten": r, "risk": _risk(o, r)})

    # merge adjacent changed segments
    merged: list[dict[str, Any]] = []
    for seg in raw:
        prev = merged[-1] if merged else None
        if seg["type"] == "changed" and prev and prev["type"] == "changed":
            prev["original"] = (prev["original"] + " " + seg["original"]).strip()
            prev["rewritten"] = (prev["rewritten"] + " " + seg["rewritten"]).strip()
            # escalate risk
            if prev["risk"] == "number" or seg["risk"] == "number":
                prev["risk"] = "number"
            elif prev["risk"] == "meaning" or seg["risk"] == "meaning":
                prev["risk"] = "meaning"
        else:
            merged.append(dict(seg))
    return merged


def _style_counts(text: str) -> dict[str, Any]:
    groups = find_matches(text)
    by_pattern = [{"id": g["id"], "name": g["name"], "count": g["count"]} for g in groups]
    strong = sum(g["count"] for g in groups if g.get("weight") == "strong")
    weak = sum(g["count"] for g in groups if g.get("weight") == "weak")
    return {"total": strong + weak, "strong": strong, "weak": weak, "by_pattern": by_pattern}


def style_report(original: str, rewritten: str) -> dict[str, Any]:
    before = _style_counts(original)
    after = _style_counts(rewritten)
    remaining = [{"id": p["id"], "name": p["name"], "count": p["count"]} for p in after["by_pattern"]]
    # changed words pct
    a = _tokens(original)
    b = _tokens(rewritten)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        changed += max(i2 - i1, j2 - j1)
    denom = max(len(a), 1)
    changed_words_pct = round(100 * changed / denom)
    return {
        "before": before,
        "after": after,
        "removed": max(0, before["total"] - after["total"]),
        "remaining": remaining,
        "changed_words_pct": changed_words_pct,
    }
