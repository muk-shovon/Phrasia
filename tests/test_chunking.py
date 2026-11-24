"""Chunking must be lossless when the outputs are reassembled."""
from __future__ import annotations

from backend.core.chunking import assemble_outputs, split_into_chunks


def _round_trip(text: str, budget: int) -> str:
    chunks = split_into_chunks(text, budget=budget)
    return assemble_outputs([(chunk.separator, chunk.text) for chunk in chunks])


def test_single_short_paragraph() -> None:
    text = "One short sentence."
    chunks = split_into_chunks(text, budget=1_000)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].separator == ""
    assert _round_trip(text, 1_000) == text


def test_paragraph_breaks_are_preserved() -> None:
    text = "First paragraph here.\n\nSecond paragraph here.\n\n\nThird one."
    assert _round_trip(text, 1_000) == text


def test_long_paragraph_is_split_without_losing_text() -> None:
    sentence = "This is a reasonably long sentence used for chunk testing. "
    text = (sentence * 30).strip()
    chunks = split_into_chunks(text, budget=400)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 400 for chunk in chunks)
    assert _round_trip(text, 400) == text


def test_long_word_is_hard_split() -> None:
    text = "x" * 1_200
    chunks = split_into_chunks(text, budget=250)
    assert len(chunks) >= 5
    assert _round_trip(text, 250) == text


def test_empty_input_yields_no_chunks() -> None:
    assert split_into_chunks("   \n\n  ") == []
