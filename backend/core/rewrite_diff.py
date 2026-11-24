"""Diff and style-check helpers for humanize output."""
from __future__ import annotations

import difflib
import re
from typing import Any

from backend.core.ai_patterns import find_matches, get_banned_words

_WORD_RE = re.compile(r"\S+")
_NUM_RE = re.compile(r"\d+(?:[\.,]\d+)?")
_HEDGE_MODAL_NEG_QUANT = {
    "may","might","can","could","should","must","would","shall",
    "always","usually","often","rarely","never","sometimes","generally",
    "not","no","n't","none","neither","nor","without",
    "all","every","some","any","few","many","most","several","only","just",
}
_EQUIV_GROUPS = [
    {"yet","but","however"},
    {"has become","is now","became"},
    {"zero","no","none"},
    {"only","just"},
    {"can","is able to","able to"},
    {"because","since","as"},
    {"using","by using","with"},
]
_EQUIV_MAP: dict[str, set[str]] = {}
for _g in _EQUIV_GROUPS:
    for _w in _g:
        _EQUIV_MAP.setdefault(_w.lower(), set()).update(x.lower() for x in _g)


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(_norm_ws(text))


def _word_key(w: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", w.lower())


def _words_only(text: str) -> list[str]:
    return [k for k in (_word_key(w) for w in _tokens(text)) if k]


def _punct_only_change(a: str, b: str) -> bool:
    return _words_only(a) == _words_only(b) and _norm_ws(a) != _norm_ws(b)


def _has_number_change(a: str, b: str) -> bool:
    return _NUM_RE.findall(a) != _NUM_RE.findall(b)


def _equivalent(a: str, b: str) -> bool:
    al, bl = _norm_ws(a).lower(), _norm_ws(b).lower()
    if al == bl:
        return True
    # normalize for phrase lookup
    al_n = " ".join(_words_only(al))
    bl_n = " ".join(_words_only(bl))
    if al_n == bl_n:
        return True
    # phrase/single equivalence
    for g in _EQUIV_GROUPS:
        gn = [" ".join(_words_only(x)) for x in g]
        # direct
        if al_n in gn and bl_n in gn:
            return True
        # phrase embedded in longer text
        for x in gn:
            for y in gn:
                if x == y: continue
                if al_n.replace(x, y) == bl_n or bl_n.replace(y, x) == al_n:
                    return True
    # token-level single word equivalence
    ak = [x for x in (_word_key(x) for x in _tokens(al)) if x]
    bk = [x for x in (_word_key(x) for x in _tokens(bl)) if x]
    if len(ak) == 1 and len(bk) == 1:
        return bk[0] in {_word_key(x) for x in _EQUIV_MAP.get(ak[0], {ak[0]})}
    return False


def _meaning_flags_from_source(source: str, rewritten: str) -> bool:
    # flag only when hedge/modal/negation/quantifier from SOURCE is missing or changed
    s_low = _norm_ws(source).lower()
    r_low = _norm_ws(rewritten).lower()
    s_toks = set(_words_only(source))
    r_toks = set(_words_only(rewritten))
    for w in _HEDGE_MODAL_NEG_QUANT:
        wk = _word_key(w)
        if not wk: continue
        in_s = wk in s_toks or (w in s_low)
        in_r = wk in r_toks or (w in r_low)
        if in_s and not in_r:
            # check equivalence - if any equivalent present in r, ignore
            eq = _EQUIV_MAP.get(wk, set())
            if any(_word_key(e) in r_toks for e in eq):
                continue
            return True
    return False


def _risk(a: str, b: str, source_sentence: str | None = None) -> str:
    a, b = _norm_ws(a), _norm_ws(b)
    if not a or not b:
        t = a or b
        if _NUM_RE.search(t):
            return "number"
        # if deleted/inserted content is just punctuation
        if not _words_only(t):
            return "none"
        # for pure insert/delete, flag meaning only if substantive and not equivalent
        return "meaning" if len(_words_only(t)) > 0 else "none"
    if _punct_only_change(a, b):
        return "none"
    if _has_number_change(a, b):
        return "number"
    if _equivalent(a, b):
        return "none"
    aw, bw = _words_only(a), _words_only(b)
    if aw == bw:
        return "none"
    src = source_sentence or a
    if _meaning_flags_from_source(src, b):
        return "meaning"
    return "none"


def _merge_changed(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for seg in raw:
        prev = merged[-1] if merged else None
        if seg["type"] == "changed" and prev and prev["type"] == "changed":
            prev["original"] = (prev["original"] + " " + seg["original"]).strip()
            prev["rewritten"] = (prev["rewritten"] + " " + seg["rewritten"]).strip()
            if prev.get("risk") == "number" or seg.get("risk") == "number":
                prev["risk"] = "number"
            elif prev.get("risk") == "meaning" or seg.get("risk") == "meaning":
                prev["risk"] = "meaning"
        else:
            merged.append(dict(seg))
    return merged


def diff_segments(original: str, rewritten: str) -> list[dict[str, Any]]:
    original, rewritten = _norm_ws(original), _norm_ws(rewritten)
    a = _tokens(original)
    b = _tokens(rewritten)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    raw: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        o = " ".join(a[i1:i2])
        r = " ".join(b[j1:j2])
        if tag == "equal":
            if o:
                raw.append({"type": "equal", "text": o, "original": o, "risk": "none"})
        elif _punct_only_change(o, r):
            txt = r or o
            if txt:
                raw.append({"type": "equal", "text": txt, "original": o, "risk": "none"})
        else:
            raw.append({"type": "changed", "original": o, "rewritten": r, "risk": _risk(o, r, o)})
    return _merge_changed(raw)


def diff_from_alignment(alignment: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Word diff per aligned sentence pair."""
    segs: list[dict[str, Any]] = []
    for pair in alignment:
        src = str(pair.get("source_text", ""))
        out = str(pair.get("output_text", ""))
        low = bool(pair.get("low_change", False))
        flat = bool(pair.get("flat_rhythm", False))
        pair_risks = set(pair.get("risk_flags") or [])
        a = _tokens(src)
        b = _tokens(out)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        raw: list[dict[str, Any]] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            o = " ".join(a[i1:i2])
            r = " ".join(b[j1:j2])
            if tag == "equal":
                if o:
                    raw.append({"type": "equal", "text": o, "original": o, "risk": "none", "low_change": low, "flat_rhythm": flat, "sentence": True})
            elif _punct_only_change(o, r):
                txt = r or o
                if txt:
                    raw.append({"type": "equal", "text": txt, "original": o, "risk": "none", "low_change": low, "flat_rhythm": flat, "sentence": True})
            else:
                risk = _risk(o, r, src)
                if "number" in pair_risks: risk = "number"
                raw.append({"type": "changed", "original": o, "rewritten": r, "risk": risk, "low_change": low, "flat_rhythm": flat, "sentence": True})
        merged = _merge_changed(raw)
        # mark sentence boundary - wrap in a sentence group marker on first segment
        if merged:
            merged[0]["sentence_start"] = True
            merged[-1]["sentence_end"] = True
            for m in merged:
                m["low_change"] = low
                m["flat_rhythm"] = flat
        segs.extend(merged)
        # space between sentences
        segs.append({"type": "equal", "text": " ", "original": " ", "risk": "none", "low_change": False, "sentence_space": True})
    if segs and segs[-1].get("sentence_space"):
        segs.pop()
    return segs


def _style_counts(text: str) -> dict[str, Any]:
    groups = find_matches(text)
    by_pattern = [{"id": g["id"], "name": g["name"], "count": g["count"]} for g in groups]
    strong = sum(g["count"] for g in groups if g.get("weight") == "strong")
    weak = sum(g["count"] for g in groups if g.get("weight") == "weak")
    return {"total": strong + weak, "strong": strong, "weak": weak, "by_pattern": by_pattern}


def structure_stats(alignment: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not alignment:
        return {"sentences_total": 0, "sentences_restructured": 0, "average_change_pct": 0}
    total = 0
    restructured = 0
    for p in alignment:
        n = max(1, len(p.get("source_indices") or []))
        total += n
        if not p.get("low_change", False):
            restructured += n
    avg = round(100 * sum((1 - float(p.get("similarity", 1.0))) * max(1, len(p.get("source_indices") or [])) for p in alignment) / max(total, 1))
    return {"sentences_total": total, "sentences_restructured": restructured, "average_change_pct": avg}


def style_report(original: str, rewritten: str, alignment: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    before = _style_counts(original)
    after = _style_counts(rewritten)
    remaining = [{"id": p["id"], "name": p["name"], "count": p["count"]} for p in after["by_pattern"]]
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
    # banned words removed (simple count in original vs rewritten)
    import re as _re
    bw = get_banned_words()
    def _bw_count(txt: str) -> int:
        low = txt.lower(); n = 0
        for w in bw:
            if w == "not only ... but also":
                n += len(_re.findall(r"\bnot\s+only\b.{0,80}\bbut\s+also\b", low))
            else:
                n += len(_re.findall(r"(?<!\w)" + _re.escape(w.lower()) + r"(?!\w)", low))
        return n
    banned_removed = max(0, _bw_count(original) - _bw_count(rewritten))

    # rhythm varied: paragraphs not all-flat
    paras = [p for p in _re.split(r"\n\s*\n", rewritten.strip()) if p.strip()]
    rhythm_varied = 0
    for para in paras:
        sents = [x.strip() for x in _re.split(r"(?<=[.!?])\s+", para) if x.strip()]
        lens = [len(_WORD_RE.findall(x)) for x in sents]
        if len(lens) < 3:
            rhythm_varied += 1
            continue
        if max(lens) <= min(lens) * 1.25 and (max(lens) - min(lens)) <= max(2, min(lens)*0.2):
            pass  # flat
        else:
            rhythm_varied += 1
    return {
        "before": before,
        "after": after,
        "removed": max(0, before["total"] - after["total"]),
        "remaining": remaining,
        "changed_words_pct": changed_words_pct,
        "banned_words_removed": banned_removed,
        "rhythm_varied": rhythm_varied,
        "paragraphs_total": len(paras),
        "structure": structure_stats(alignment),
    }
