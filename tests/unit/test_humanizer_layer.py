"""Tests for the local humanizer post-processing layer.

The layer itself is supplied verbatim; these tests guard its integration
contract and the behaviours required by the integration prompt.
"""
from __future__ import annotations

import re

from humanizer_layer import humanize_layer


def test_empty_and_whitespace_input_unchanged() -> None:
    assert humanize_layer("", seed=1) == ""
    assert humanize_layer("   \n  ", seed=1) == "   \n  "


def test_same_seed_is_reproducible() -> None:
    text = "Furthermore, it is important to note that this utilizes a robust approach."
    first = humanize_layer(text, strength=0.8, seed=42)
    second = humanize_layer(text, strength=0.8, seed=42)
    assert first == second


def test_urls_quotes_and_code_are_never_altered() -> None:
    url = "https://example.com/a?b=1"
    quoted = '"It is important to note that this is fine."'
    inline = "`it is important to note that`"
    fenced = "```\nit is important to note that\n```"
    text = f"See {url}. As the report says, {quoted} Also {inline}.\n{fenced}"

    result = humanize_layer(text, strength=1.0, seed=3)

    assert url in result
    assert quoted in result
    assert inline in result
    assert fenced in result


def test_formal_true_produces_no_contractions() -> None:
    text = (
        "It is clear that we do not know. They are here, and cannot leave. "
        "We will see if it is useful."
    )
    result = humanize_layer(text, strength=1.0, seed=7, formal=True)

    for contraction in ("it's", "don't", "they're", "can't", "we'll", "won't"):
        assert contraction not in result.lower()


def test_strength_zero_leaves_ordinary_text_unchanged() -> None:
    text = "The tool is useful. It is fast."
    assert humanize_layer(text, strength=0.0, seed=1) == text


def test_markdown_structure_is_preserved() -> None:
    markdown = (
        "# Title\n\n"
        "- first item here\n"
        "- second item here\n\n"
        "## Subtitle\n\n"
        "1. one thing\n"
        "2. another thing"
    )
    result = humanize_layer(markdown, strength=1.0, seed=5)

    before = [line for line in markdown.splitlines() if line.strip()]
    after = [line for line in result.splitlines() if line.strip()]
    assert len(before) == len(after)
    for original, processed in zip(before, after):
        assert original.split(maxsplit=1)[0] == processed.split(maxsplit=1)[0]


def test_cleanup_removes_spacing_artifacts() -> None:
    text = (
        "Furthermore, it is important to note that this is significant , "
        "and it is robust . Also , it is useful ."
    )
    result = humanize_layer(text, strength=1.0, seed=9)

    assert "  " not in result
    assert " ," not in result
    assert " ." not in result
    assert not re.search(r"[.!?]\s+[a-z]", result)


def test_articles_are_grammatical() -> None:
    text = (
        "This is a important point. It is an robust result. "
        "It is a unique case. It took an hour."
    )
    result = humanize_layer(text, strength=0.0, seed=1)

    for wrong in ("a important", "an robust", "an unique", "a hour", "a honest"):
        assert wrong not in result
    assert "an important point" in result
    assert "a robust result" in result
