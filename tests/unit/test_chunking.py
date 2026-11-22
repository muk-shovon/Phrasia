"""Tests for chunking service."""
from __future__ import annotations

import pytest
from core.chunking_service import Chunker
from phrasia_domain import ChunkPlan


def test_empty_text_returns_no_chunks() -> None:
    c = Chunker()
    assert c.chunk("") == []
    assert c.chunk("   ") == []


def test_single_paragraph_returns_one_chunk() -> None:
    c = Chunker(max_input_tokens=100)
    text = "This is a single paragraph."
    chunks = c.chunk(text)
    assert len(chunks) >= 1
    assert all(isinstance(ch, ChunkPlan) for ch in chunks)


def test_multiple_paragraphs_can_split_into_multiple_chunks() -> None:
    # Very small budget forces splits
    c = Chunker(max_input_tokens=2, output_reserve_tokens=0)
    text = "\n\n".join([f"Paragraph {i}" for i in range(5)])
    chunks = c.chunk(text)
    assert len(chunks) >= 2
    # Chunks must be in order
    for i, ch in enumerate(chunks):
        assert ch.sequence_index == i


def test_protected_urls_survive_masking() -> None:
    c = Chunker()
    url = "https://example.com/some-path?foo=bar"
    text = f"Some text {url} more text"
    chunks = c.chunk(text)
    # The URL should remain in the source_text of at least one chunk
    combined = "".join(ch.source_text for ch in chunks)
    assert url in combined


def test_source_hashes_are_deterministic() -> None:
    c = Chunker()
    text = "Hello world. This is a test."
    c1 = c.chunk(text)
    c2 = c.chunk(text)
    assert [ch.source_hash for ch in c1] == [ch.source_hash for ch in c2]