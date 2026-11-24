"""The style signal must stay honest: no percentage, no verdict."""
from __future__ import annotations

from backend.core.detector import DISCLAIMER, analyze

FORMULAIC = (
    "Furthermore, it is important to note that this is a pivotal moment. "
    "Let's dive in. This is not just a tool, but a game-changer. "
    "In conclusion, I hope this helps!"
)


def test_detector_has_no_percentage_or_verdict() -> None:
    result = analyze(FORMULAIC)
    assert "percent" not in str(result).lower()
    assert "%" not in str(result)
    assert "verdict" not in result
    assert "label" not in result


def test_detector_returns_pattern_groups() -> None:
    result = analyze(FORMULAIC)
    assert result["disclaimer"] == DISCLAIMER
    assert "not proof of authorship" in result["disclaimer"].lower()
    assert isinstance(result["patterns"], list)
    assert result["total_matches"] >= 1
    assert result["word_count"] > 0
    for g in result["patterns"]:
        assert g["name"]
        assert g["hint"]
        assert g["count"] >= 1
        assert isinstance(g["matches"], list)


def test_clean_text_can_have_zero_matches() -> None:
    result = analyze("I went to the store and bought bread. It was fresh.")
    assert result["total_matches"] >= 0
    assert "percent" not in str(result).lower()
