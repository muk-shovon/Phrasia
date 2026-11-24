"""Rebuild text from blocks with the original separators."""
from __future__ import annotations

from dataclasses import replace

from backend.engine.blocks import Block


def assemble(blocks: list[Block], texts: list[str] | None = None) -> str:
    """Join blocks, optionally replacing their text while keeping separators."""
    parts: list[str] = []
    for index, block in enumerate(blocks):
        text = texts[index] if texts is not None and index < len(texts) else block.text
        parts.append(f"{block.prefix}{text}{block.suffix}")
    return "".join(parts)


def with_text(blocks: list[Block], new_texts: list[str]) -> list[Block]:
    """Return copies of blocks with replaced text."""
    if len(new_texts) != len(blocks):
        raise ValueError("One replacement per block is required.")
    return [replace(block, text=text) for block, text in zip(blocks, new_texts)]
