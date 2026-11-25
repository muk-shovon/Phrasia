"""The catalog scanner is the one source for all writing-pattern signals."""
from __future__ import annotations

from backend.core import detector
from backend.engine import ranker
from backend.engine.skill import scan


def _ids(text: str, **options: bool) -> set[str]:
    return {tell["id"] for tell in scan.scan(text, options or None)}


def test_catalog_covers_sections_one_through_twenty_six() -> None:
    assert scan.sections() == list(range(1, 27))
    assert not any(tell["section"] == 26 for tell in scan.scan("A short reply."))


def test_scanner_skips_quotes_code_titles_names_and_phrase_discussion() -> None:
    text = (
        'She quoted "Great question!" and typed `Furthermore -- continue`.\n'
        "## Here's What You Need To Know\n"
        "They called the phrase 'at its core' stale.\n"
        "We visited Vibrant Valley yesterday.\n"
        "Vibrant Valley opened today."
    )
    tells = scan.scan(text)
    assert [tell["id"] for tell in tells] == ["heading-titlecase"]


def test_weak_tells_need_other_sections_but_dashes_do_not() -> None:
    assert "hyphen-after-verb" not in _ids("The report is high-quality.")
    clustered = "The report is high-quality. It could potentially work. He said \u201cyes\u201d."
    assert {"hyphen-after-verb", "qualifier-stack", "curly-quotes"} <= _ids(clustered)
    assert "hyphen-after-verb" in _ids(
        "The report is high-quality, the process is well-documented, and the plan is long-term."
    )
    assert "dashes" in _ids("The policy \u2014 announced today \u2014 starts Friday.")
    assert "dashes" not in _ids(
        "The policy \u2014 announced today \u2014 starts Friday.", replace_dashes=False
    )


def test_shape_checks_cover_closers_parallelism_and_openings() -> None:
    text = (
        "Caching cuts repeat work.\n\nThat is the real win.\n\n"
        "Retries hide brief outages.\n\nThat is the real win."
    )
    assert "closer-identical" in _ids(text)
    assert "repeated-openings" in _ids(
        "She noted the door. She noted the lock. She filed both away."
    )
    assert "triad-paragraph" in _ids(
        "A career can fail. A relationship can end. A skill can go unused."
    )


def test_detector_and_ranker_use_the_scanner() -> None:
    text = "Great question! The report is pivotal."
    expected = len(scan.scan(text))
    assert detector.analyze(text)["total_matches"] == expected
    assert ranker.pattern_count(text) == expected
