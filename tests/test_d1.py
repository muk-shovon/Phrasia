"""Pattern signal, input hygiene and honest output."""
from __future__ import annotations

from backend.core.detector import analyze, find_matches
from backend.engine.clean import clean


def test_pattern_matching_groups() -> None:
    groups = find_matches("Furthermore, this is a great question. I hope this helps! Let's dive in.")
    assert groups
    assert all(group["count"] >= 1 and group["matches"] for group in groups)


def test_invisible_char_cleaning() -> None:
    raw = "Hello\u200b world\u200c!\u2060 This\u00a0is\uFEFF clean."
    assert clean(raw) == "Hello world! This is clean."


def test_detector_output_has_no_percentage_or_verdict() -> None:
    result = analyze("Furthermore, it is important to note that this is pivotal.")
    assert "%" not in str(result)
    assert "percent" not in str(result).lower()
    assert "verdict" not in result
    assert "label" not in result
    assert "not proof of authorship" in result["disclaimer"].lower()
