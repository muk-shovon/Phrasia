"""Pure-Python engine modules: parsing, protection and validation."""
from __future__ import annotations

from pathlib import Path

from backend.engine import assemble, blocks, clean, clauses, lexicon, protect, sentences, validators

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_clean_removes_invisibles_and_normalizes_spaces() -> None:
    raw = "Hello\u200b world\u200c!\u2060 This\u00a0is\uFEFF clean."
    assert clean.clean(raw) == "Hello world! This is clean."


def test_paragraph_round_trip() -> None:
    text = (FIXTURES / "remote_work.txt").read_text(encoding="utf-8")
    parsed = blocks.parse(text)
    assert len(parsed) == 1
    assert parsed[0].kind == "paragraph"
    assert assemble.assemble(parsed) == text


def test_bullets_keep_markers_and_one_item_per_line() -> None:
    text = (FIXTURES / "bullets.txt").read_text(encoding="utf-8")
    parsed = blocks.parse(text)
    assert len(parsed) == 3
    assert all(block.kind == "bullet" for block in parsed)
    assert [block.marker for block in parsed] == ["•", "•", "•"]
    assert [block.label for block in parsed] == ["Clarity", "Timing", "Safety"]
    assert all(block.body and "\n" not in block.body for block in parsed)
    assert assemble.assemble(parsed) == text


def test_heading_and_label_detection() -> None:
    parsed = blocks.parse("Notes\n\n• Risk: Small.\n1. Step: Do it.\n")
    assert parsed[0].kind == "heading"
    assert parsed[1].label == "Risk"
    assert parsed[2].marker == "1."
    assert assemble.assemble(parsed) == "Notes\n\n• Risk: Small.\n1. Step: Do it.\n"


def test_protected_spans_round_trip() -> None:
    text = (
        "See https://example.com/a?b=1 and ada@example.com. Code `x = 1` stays. "
        "Reference [1, 3] matters. She said \"this must stay\" during the call. "
        "It took 3 hours and cost $50."
    )
    masked, spans = protect.extract(text)
    assert spans
    assert all(span.placeholder in masked for span in spans)
    assert protect.restore(masked, spans) == text
    assert protect.restore(masked.replace(spans[0].placeholder, ""), spans) is None


def test_splitter_edge_cases() -> None:
    text = "Dr. Smith met Ada in 3.14 hours. It worked. Wait... Really?"
    parts = sentences.texts(text)
    assert parts[0].startswith("Dr. Smith")
    assert "3.14 hours." in parts[0]
    assert parts[1] == "It worked."
    assert "Wait..." in " ".join(parts)
    assert parts[-1] == "Really?"


def test_lexicon_and_clauses() -> None:
    assert lexicon.guess("may") == "modal"
    assert lexicon.guess("carefully") == "adverb"
    assert lexicon.guess("agreement") == "noun"
    parts = clauses.split("Managers can help, but employees may need time, so plans change.")
    assert len(parts) >= 2
    assert any("but" in clauses.markers(part) for part in parts)


def test_validators_accept_good_and_reject_bad() -> None:
    source = "Employees may need 3 days to finish."
    good = "Employees might need 3 days to finish."
    ok, reasons = validators.validate(source, good)
    assert ok, reasons

    bad_number = "Employees may need 4 days to finish."
    assert not validators.preserve_critical(source, bad_number)

    bad_hedge = "Employees need 3 days to finish."
    assert "critical" in validators.validate(source, bad_hedge)[1]

    bad_content = "Employees may need 3 things."
    assert "content" in validators.validate(source, bad_content)[1]

    bad_grammar = "employees may need 3 days to finish"
    assert "grammar" in validators.validate(source, bad_grammar)[1]

    bad_length = "Employees finish."
    assert "length" in validators.validate(source, bad_length)[1]


def test_validators_check_split_subjects() -> None:
    assert validators.grammar_sanity("Employees helped. Managers listened.")
    assert not validators.grammar_sanity("Ran quickly. Then left.")
