"""STEP E2 tests: style check, diff, forbidden terms."""
from __future__ import annotations

import re
from pathlib import Path

from backend.core.rewrite_diff import style_report, diff_segments

FORBIDDEN_TERMS = [
    "turnitin", "gptzero", "copyleaks", "quillbot", "zerogpt", "originality.ai",
    "originality", "sapling", "ai score",
]
FORBIDDEN_WORDS = ["bypass", "undetectable", "passes"]


def _scan_blob(blob: str) -> list[str]:
    low = blob.lower()
    hits = [t for t in FORBIDDEN_TERMS if t in low]
    for w in FORBIDDEN_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", low):
            hits.append(w)
    return hits


def test_style_counts_before_after() -> None:
    original = "Furthermore, this is a great question. I hope this helps! Let's dive in."
    rewritten = "Here is a direct answer."
    report = style_report(original, rewritten)
    assert report["before"]["total"] >= 2
    assert report["after"]["total"] <= report["before"]["total"]
    assert isinstance(report["removed"], int)
    assert isinstance(report["remaining"], list)
    assert 0 <= report["changed_words_pct"] <= 100


def test_diff_segments_have_risk_flags() -> None:
    segs = diff_segments("I have 2 cats.", "I have 3 cats.")
    assert any(s["type"] == "changed" and s["risk"] == "number" for s in segs)


def test_forbidden_words_not_in_frontend_source() -> None:
    root = Path(__file__).resolve().parents[1] / "frontend" / "src"
    texts = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in {".ts", ".css", ".html"}:
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    hits = _scan_blob("\n".join(texts))
    assert not hits, f"Forbidden terms in frontend source: {hits}"


def test_forbidden_words_not_in_api_responses(client) -> None:
    r = client.post("/api/detector/check", json={"text": "Furthermore, this is a great question. I hope this helps!"})
    assert r.status_code == 200
    hits = _scan_blob(r.text)
    assert not hits, f"Forbidden terms in detector response: {hits}"
    r = client.post("/api/diff", json={"original": "Furthermore, great question.", "rewritten": "Here is the answer."})
    assert r.status_code == 200
    hits = _scan_blob(r.text)
    assert not hits, f"Forbidden terms in diff response: {hits}"
