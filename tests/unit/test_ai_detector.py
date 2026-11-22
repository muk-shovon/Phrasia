"""Tests for the local writing-style detector."""
from __future__ import annotations

from core.ai_detector import HUMAN_THRESHOLD, scan, score_sentence

AI_TEXT = (
    "Furthermore, it is important to note that artificial intelligence has become "
    "an integral part of modern society. Moreover, the utilization of machine learning "
    "algorithms has facilitated significant advancements in various domains. "
    "In conclusion, it is crucial to leverage these robust technologies in order to "
    "navigate the ever-evolving landscape of innovation."
)

HUMAN_TEXT = (
    "AI's basically woven into everything we do now. And machine learning, in particular, "
    "has pushed several fields forward in ways that genuinely count. We should keep "
    "working with these tools as they evolve—that's just where we're at."
)


def test_detector_separates_ai_and_human_text() -> None:
    ai = scan(AI_TEXT)
    human = scan(HUMAN_TEXT)
    assert ai.normal_score < HUMAN_THRESHOLD
    assert human.normal_score >= HUMAN_THRESHOLD
    assert ai.verdict == "AI Detected"
    assert human.verdict == "Looks Human"


def test_detector_is_per_sentence() -> None:
    result = scan(AI_TEXT)
    assert len(result.sentences) == 3
    assert [s.id for s in result.sentences] == [0, 1, 2]
    assert all(not s.looks_human for s in result.sentences)


def test_detector_reports_reasons() -> None:
    text = (
        "Furthermore, it is important to note that artificial intelligence has become "
        "an integral part of modern society and a great many other domains."
    )
    s = score_sentence(text, 0)
    assert any("stock opener" in r for r in s.reasons)
    assert s.score < HUMAN_THRESHOLD


def test_detector_bonus_for_contractions_and_short_sentences() -> None:
    s = score_sentence("That's the way it works.", 0)
    assert s.score >= HUMAN_THRESHOLD


def test_detector_handles_empty_input() -> None:
    result = scan("")
    assert result.sentences == []
    assert result.normal_score == 1.0
