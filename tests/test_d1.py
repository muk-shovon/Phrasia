"""STEP D1 feature tests (mocked, no network)."""
from __future__ import annotations

import pytest

from backend.core.ai_patterns import find_matches, get_patterns
from backend.core.detector import analyze
from backend.core.input_hygiene import clean_invisible_characters
from backend.core.prompt import HumanizeOptions, build_system_prompt
from backend.core import humanizer
from backend.config import MAX_WORDS_PER_REQUEST


def test_pattern_matching_groups() -> None:
    patterns = get_patterns()
    assert len(patterns) >= 20
    text = "Furthermore, this is a great question. I hope this helps! Let's dive in."
    groups = find_matches(text)
    names = {g["name"] for g in groups}
    assert any("Filler transitions" == n or "Chatbot residue" == n or "Staged run-up" == n for n in names)
    assert all(g["count"] >= 1 and g["matches"] for g in groups)



def test_invisible_char_cleaning() -> None:
    raw = "Hello\u200b world\u200c!\u2060 This\u00a0is\uFEFF clean."
    cleaned = clean_invisible_characters(raw)
    assert "\u200b" not in cleaned
    assert "\u200c" not in cleaned
    assert "\u2060" not in cleaned
    assert "\uFEFF" not in cleaned
    assert "\u00a0" not in cleaned
    assert "Hello world! This is clean." == cleaned


def test_word_cap_enforced(monkeypatch) -> None:
    monkeypatch.setattr("backend.core.humanizer.MAX_WORDS_PER_REQUEST", 5)
    with pytest.raises(ValueError) as exc:
        humanizer.create_job("one two three four five six")
    assert "5 words" in str(exc.value)


def test_detector_output_has_no_percentage_field() -> None:
    result = analyze("Furthermore, it is important to note that this is pivotal.")
    assert "%" not in str(result)
    assert "percent" not in str(result).lower()
    assert "verdict" not in result
    assert "label" not in result
    assert "disclaimer" in result
    assert "not proof of authorship" in result["disclaimer"].lower()
