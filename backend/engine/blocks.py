"""Paragraph, list and heading parsing that keeps exact separators."""
from __future__ import annotations

import re
from dataclasses import dataclass

_BULLET = re.compile(r"^(\s*)([•▪◦*\u2013-]|\d+[.)])(\s+)(.+)$")
_LABEL = re.compile(r"^([^:]{1,120}):\s+(.+)$")
_HEADING_MARK = re.compile(r"^\s*#{1,6}\s+")


@dataclass
class Block:
    kind: str
    text: str
    prefix: str = ""
    suffix: str = ""
    marker: str = ""
    label: str = ""
    body: str = ""


def _classify(line: str) -> tuple[str, str, str, str]:
    marker = label = body = ""
    match = _BULLET.match(line)
    if match:
        marker = match.group(2)
        content = match.group(4)
        kind = "bullet"
    elif _HEADING_MARK.match(line):
        content = line.strip()
        kind = "heading"
    else:
        content = line.strip()
        is_short = len(content) <= 80 and len(content.split()) <= 10
        punctuation = ".!?:;" 
        is_heading = is_short and not content.endswith(tuple(punctuation)) and ":" not in content
        kind = "heading" if is_heading else "paragraph"
    labelled = _LABEL.match(content)
    if labelled and len(labelled.group(1).split()) <= 6:
        label = labelled.group(1).strip()
        body = labelled.group(2).strip()
    return kind, marker, label, body


def parse(text: str) -> list[Block]:
    """Split text into blocks; every newline and blank line is retained."""
    blocks: list[Block] = []
    pending = ""
    for line in (text or "").splitlines(keepends=True):
        content = line.rstrip("\r\n")
        ending = line[len(content):]
        if not content.strip():
            pending += line
            continue
        kind, marker, label, body = _classify(content)
        blocks.append(
            Block(
                kind=kind,
                text=content,
                prefix=pending,
                suffix=ending,
                marker=marker,
                label=label,
                body=body,
            )
        )
        pending = ""
    if not blocks:
        return [Block(kind="empty", text="", suffix=pending)] if pending else []
    blocks[-1].suffix += pending
    return blocks


def label_body(block: Block) -> tuple[str, str]:
    """Return the label and body of a block, or empty strings."""
    return block.label, block.body
