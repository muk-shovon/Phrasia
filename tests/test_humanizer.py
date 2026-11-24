"""Pure-Python rewriting: structure, safety and the word cap."""
from __future__ import annotations

import pytest

from backend.config import MAX_WORDS_PER_REQUEST
from backend.core import humanizer

FIXTURE = (
    "Remote work has become a widespread part of how many organizations operate today, so working remotely isn't always easy. "
    "Through digital tools, employees can communicate, share information, and work together even when they're in diverse locations. "
    "Some employees may feel disconnected from their teams, while others struggle to balance work responsibilities with personal life."
)


def test_word_cap_enforced() -> None:
    with pytest.raises(ValueError, match="limit"):
        humanizer.humanize(" ".join(["word"] * (MAX_WORDS_PER_REQUEST + 1)))


def test_fixture_restructures_sentences() -> None:
    result = humanizer.humanize(FIXTURE, strength="heavy")
    assert result["summary"]["sentences_total"] == 3
    assert result["summary"]["sentences_restructured"] >= 1
    assert "Through digital tools" not in result["text"] or "through digital tools" in result["text"]
    assert "may" in result["text"]
    assert "isn't" in result["text"] or "is not" in result["text"]


def test_unsafe_sentence_is_kept_unchanged() -> None:
    source = "https://example.com/notes contains 42 samples."
    result = humanizer.humanize(source)
    assert result["text"] == source
    assert result["summary"]["unchanged_sentences"] == 1
    assert result["alignment"][0]["low_change"] is True


def test_banned_word_in_source_is_replaced() -> None:
    result = humanizer.humanize("Ultimately, this is crucial for teams.")
    assert "ultimately" not in result["text"].lower()
    assert "crucial" not in result["text"].lower()
    assert "important" in result["text"].lower()


def test_banned_word_inside_quote_is_kept() -> None:
    source = 'She said "this is crucial" during the meeting.'
    result = humanizer.humanize(source)
    assert '"this is crucial"' in result["text"]


def test_numbers_and_names_are_preserved() -> None:
    result = humanizer.humanize("Dr. Smith met Ada in 2024, so the plan changed, because funding fell.")
    assert "2024" in result["text"]
    assert "Smith" in result["text"]
    assert "Ada" in result["text"]


def test_clean_invisible_characters_toggle() -> None:
    source = "Hello\u200b world."
    assert "world" in humanizer.humanize(source, clean_invisible=True)["text"]
    assert "\u200b" in humanizer.humanize(source, clean_invisible=False)["text"]
