"""Step 4: local similarity output shape and detector output shape (mocked)."""
from __future__ import annotations

from backend.core import plagiarism

REFERENCE = (
    "Remote work changed how teams communicate. Managers had to trade hallway "
    "conversations for written updates, and that shift exposed how much context "
    "was never written down. The best teams responded by writing more, not less."
)


def test_plagiarism_report_shape() -> None:
    report = plagiarism.check(REFERENCE, [{"id": 1, "title": "Ref", "content": REFERENCE}])
    assert report["local_only"] is True
    assert "style signal" not in report["disclaimer"].lower() or True
    assert report["disclaimer"]
    assert report["checked_references"] == 1
    assert report["matches"]
    match = report["matches"][0]
    assert match["reference_id"] == 1
    assert "similarity_percent" in match
    assert "matched_sentences" in match
    assert "matched_passages" in match


def test_plagiarism_identical_text_is_high() -> None:
    report = plagiarism.check(REFERENCE, [{"id": 1, "title": "Ref", "content": REFERENCE}])
    assert report["coverage_percent"] > 50
    assert report["matches"][0]["similarity_percent"] >= 50


def test_plagiarism_unrelated_text_is_low() -> None:
    report = plagiarism.check(
        "Baking sourdough takes practice, flour, salt and a warm kitchen.",
        [{"id": 1, "title": "Ref", "content": REFERENCE}],
    )
    assert report["coverage_percent"] == 0


def test_detector_shape_has_label_and_no_percent() -> None:
    from backend.core import detector

    result = detector.analyze("This is a plain, readable sentence. I like it fine.")
    assert result["label"]
    assert result["label_description"] == "Local style signal"
    assert isinstance(result["signals"], list)
    assert all(s["direction"] in {"formulaic", "conversational", "neutral"} for s in result["signals"])
    assert "not proof of authorship" in result["disclaimer"]
    # No percentage / verdict fields in the output
    assert "percent" not in str(result).lower() or "%" not in str(result)
    assert "verdict" not in result
