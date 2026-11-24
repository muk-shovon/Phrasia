"""Paragraph-aware chunking that can be reassembled without losing layout."""
from __future__ import annotations

import re
from dataclasses import dataclass

PARAGRAPH_SEPARATOR = re.compile(r"\n[ \t]*\n\s*")
SENTENCE_BOUNDARY = re.compile(r"[.!?\u2026][\"'\u201d\u2019)\]]*\s+")


@dataclass(frozen=True)
class Chunk:
    """One unit of text sent to a provider.

    ``separator`` holds the exact whitespace that appeared before this chunk in
    the source. Reassembly concatenates ``separator + output`` so paragraph
    breaks are preserved instead of being re-invented.
    """

    text: str
    separator: str


def split_sentences(paragraph: str) -> list[str]:
    """Split a paragraph while keeping the trailing whitespace of each piece."""
    pieces: list[str] = []
    start = 0
    for match in SENTENCE_BOUNDARY.finditer(paragraph):
        end = match.end()
        if end > start:
            pieces.append(paragraph[start:end])
            start = end
    if start < len(paragraph):
        pieces.append(paragraph[start:])
    return [piece for piece in pieces if piece]


def _pack_sentences(paragraph: str, budget: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for sentence in split_sentences(paragraph):
        while len(sentence) > budget:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:budget])
            sentence = sentence[budget:]
        if not sentence:
            continue
        if current and len(current) + len(sentence) > budget:
            pieces.append(current)
            current = ""
        current += sentence
    if current:
        pieces.append(current)
    return pieces or [paragraph[:budget]]


def split_into_chunks(text: str, budget: int = 6_000) -> list[Chunk]:
    """Split text into chunks of at most ``budget`` characters.

    Paragraph boundaries are preferred. A paragraph longer than the budget is
    split at sentence boundaries, then hard-split as a last resort.
    """
    if budget < 200:
        raise ValueError("Chunk budget is too small.")
    stripped = text.strip()
    if not stripped:
        return []

    paragraphs = PARAGRAPH_SEPARATOR.split(stripped)
    separators = PARAGRAPH_SEPARATOR.findall(stripped)

    chunk_texts: list[tuple[str, str]] = []
    for index, paragraph in enumerate(paragraphs):
        if not paragraph:
            continue
        separator = separators[index - 1] if index > 0 else ""
        if len(paragraph) <= budget:
            chunk_texts.append((separator, paragraph))
            continue
        for offset, piece in enumerate(_pack_sentences(paragraph, budget)):
            chunk_texts.append((separator if offset == 0 else "", piece))

    # Group small consecutive paragraphs back together while staying under budget.
    merged: list[tuple[str, str]] = []
    for separator, piece in chunk_texts:
        if merged:
            previous_separator, previous_text = merged[-1]
            if len(previous_text) + len(separator) + len(piece) <= budget:
                merged[-1] = (previous_separator, previous_text + separator + piece)
                continue
        merged.append((separator, piece))

    return [Chunk(text=piece, separator=separator) for separator, piece in merged]


def assemble_outputs(pairs: list[tuple[str, str]]) -> str:
    """Join ``(separator, output)`` pairs back into a single document."""
    return "".join(f"{separator}{output}" for separator, output in pairs).strip()
