"""Local similarity check behaviour."""
from __future__ import annotations

from backend.core import plagiarism

REFERENCE = {
    "id": 1,
    "title": "My earlier essay",
    "content": (
        "Remote work changed how teams communicate. Managers had to trade hallway "
        "conversations for written updates, and that shift exposed how much context "
        "was never written down. The best teams responded by writing more, not less, "
        "and by making decisions visible to everyone who was not in the room."
    ),
}


def test_identical_text_is_fully_flagged() -> None:
    report = plagiarism.check(str(REFERENCE["content"]), [REFERENCE])
    assert report["coverage_percent"] == 100
    assert report["matches"]
    assert report["matches"][0]["similarity_percent"] >= 95
    assert report["matches"][0]["matched_sentences"]


def test_unrelated_text_has_no_matches() -> None:
    report = plagiarism.check(
        "Sourdough needs patience, a warm kitchen and a scale that actually works.", 
        [REFERENCE],
    )
    assert report["matches"] == []
    assert report["coverage_percent"] == 0


def test_without_references_the_report_is_still_honest() -> None:
    report = plagiarism.check(REFERENCE["content"], [])
    assert report["local_only"] is True
    assert "not the internet" in report["disclaimer"]
    assert report["checked_references"] == 0
    assert report["notes"]


def test_internal_repetition_is_reported() -> None:
    repeated = "the quick brown fox jumps over the lazy dog again and again " * 3
    report = plagiarism.check(repeated, [])
    assert report["repeated_phrases"]
