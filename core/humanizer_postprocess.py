"""Conservative, deterministic cleanup applied after a generation pass.

This is a safety net, not a magic detector bypass. It removes the most common
model-written tics (stock transitions, buzzwords, missing contractions) without
touching facts, numbers, citations, or quoted material.
"""
from __future__ import annotations

import re

# Ordered longest-first so longer phrases win over shorter ones.
_LEADING_PHRASES = (
    "it is important to note that",
    "it's important to note that",
    "it is worth noting that",
    "it's worth noting that",
    "it should be noted that",
    "in conclusion",
    "in summary",
    "furthermore",
    "moreover",
    "additionally",
    "overall",
    "that being said",
    "with that in mind",
)

_MID_REPLACEMENTS = {
    "due to the fact that": "because",
    "in order to": "to",
    "at this point in time": "now",
    "a large number of": "many",
    "a wide range of": "many",
    "it goes without saying that": "",
}

_WORD_REPLACEMENTS = {
    "utilize": "use",
    "utilizes": "uses",
    "utilized": "used",
    "utilizing": "using",
    "leverage": "use",
    "leveraging": "using",
    "facilitate": "help",
    "facilitates": "helps",
    "commence": "start",
    "commenced": "started",
    "terminate": "end",
    "subsequently": "later",
    "nevertheless": "still",
    "furthermore": "also",
    "moreover": "also",
    "delve": "look",
    "delves": "looks",
    "tapestry": "mix",
    "realm": "area",
    "robust": "strong",
    "seamless": "smooth",
    "comprehensive": "complete",
    "multifaceted": "complex",
    "ever-evolving": "changing",
}

_CONTRACTIONS = {
    r"\bit is\b": "it's",
    r"\bdo not\b": "don't",
    r"\bdoes not\b": "doesn't",
    r"\bdid not\b": "didn't",
    r"\bis not\b": "isn't",
    r"\bare not\b": "aren't",
    r"\bwas not\b": "wasn't",
    r"\bwere not\b": "weren't",
    r"\bcannot\b": "can't",
    r"\bcan not\b": "can't",
    r"\bwill not\b": "won't",
    r"\bwould not\b": "wouldn't",
    r"\bshould not\b": "shouldn't",
    r"\bcould not\b": "couldn't",
    r"\bhave not\b": "haven't",
    r"\bhas not\b": "hasn't",
    r"\bI am\b": "I'm",
    r"\byou are\b": "you're",
    r"\bwe are\b": "we're",
    r"\bthey are\b": "they're",
    r"\bthat is\b": "that's",
    r"\bthere is\b": "there's",
}


def _match_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _strip_leading(line: str) -> str:
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    # A model sentence can stack several filler openers; strip them all.
    while True:
        for phrase in _LEADING_PHRASES:
            pattern = re.compile(r"^" + re.escape(phrase) + r"\b[\s,:-]*", re.IGNORECASE)
            match = pattern.match(stripped)
            if match:
                rest = stripped[match.end() :].lstrip()
                if not rest:
                    return line
                stripped = rest[0].upper() + rest[1:]
                break
        else:
            break
    return indent + stripped


def apply_human_touch(text: str, *, mode: str, intensity: str) -> str:
    """Return text with the most obvious machine-writing tics removed.

    ``academic`` mode skips contractions to respect its formal register.
    ``light`` intensity only strips leading stock transitions.
    """
    if not text or not text.strip():
        return text

    lines = text.split("\n")
    processed: list[str] = []
    for line in lines:
        if not line.strip():
            processed.append(line)
            continue
        new_line = _strip_leading(line)
        for phrase, replacement in _MID_REPLACEMENTS.items():
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            if replacement:
                new_line = pattern.sub(
                    lambda m, r=replacement: _match_case(m.group(0), r), new_line
                )
            else:
                new_line = pattern.sub("", new_line).lstrip()
        for original, replacement in _WORD_REPLACEMENTS.items():
            pattern = re.compile(r"\b" + re.escape(original) + r"\b", re.IGNORECASE)
            new_line = pattern.sub(
                lambda m, r=replacement: _match_case(m.group(0), r), new_line
            )
        if mode != "academic":
            for pattern, replacement in _CONTRACTIONS.items():
                new_line = re.sub(
                    pattern,
                    lambda m, r=replacement: (
                        r[:1].upper() + r[1:] if m.group(0)[:1].isupper() else r
                    ),
                    new_line,
                    flags=re.IGNORECASE,
                )
        processed.append(new_line)

    result = "\n".join(processed)
    result = re.sub(r"[ \t]{2,}", " ", result)
    # Heavier intensity allows a little more restructuring.
    if intensity == "strong":
        result = re.sub(r"\s+([,.;:!?])", r"\1", result)
    return result
