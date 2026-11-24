"""No frontend leftovers from removed features."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend" / "src"
_STALE = ["api.meta", "api.diff", "providerSel", "progressFill", "renderSettings", "retryJob", "cancelJob"]


def test_removed_feature_symbols_are_absent() -> None:
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in ROOT.rglob("*.ts")
    )
    for symbol in _STALE:
        assert symbol not in blob


def test_no_inner_html_in_humanizer() -> None:
    source = (ROOT / "pages" / "humanize.ts").read_text(encoding="utf-8")
    assert "innerHTML" not in source
    assert re.search(r"h-56 md:h-64", source)
