"""Local similarity check against the owner's reference library.

Deliberately local: no text leaves the machine, nothing is compared against the
open internet.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter
from typing import Any

from backend.core.chunking import split_sentences

_WORD = re.compile(r"[a-z0-9']+")
SHINGLE_SIZE = 5
SENTENCE_SHINGLE_SIZE = 4
SENTENCE_MATCH_THRESHOLD = 0.4
MIN_SENTENCE_WORDS = 8

DISCLAIMER = (
    "Local similarity signal only. Text is compared against your own reference "
    "library, not the internet, so a low result does not prove originality."
)


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _shingles(tokens: list[str], size: int = SHINGLE_SIZE) -> set[str]:
    if len(tokens) < size:
        return set()
    return {" ".join(tokens[start : start + size]) for start in range(len(tokens) - size + 1)}


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in split_sentences(text)
        if len(_tokens(sentence)) >= MIN_SENTENCE_WORDS
    ]


def _clip(text: str, limit: int = 280) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else f"{clean[:limit].rstrip()}…"


def _matched_passages(input_text: str, reference_text: str, limit: int = 3) -> list[dict[str, Any]]:
    """Longest verbatim-ish passages the input shares with the reference."""
    matches: list[dict[str, Any]] = []
    ratio = difflib.SequenceMatcher(None, input_text.lower(), reference_text.lower())
    for block in ratio.get_matching_blocks():
        if block.size < 24 or block.size == 0:
            continue
        passage = _clip(input_text[block.a : block.a + block.size], 220)
        if passage not in matches:
            matches.append(
                {
                    "passage": passage,
                    "length_chars": block.size,
                }
            )
        if len(matches) >= limit:
            break
    return matches


def _repeated_phrases(tokens: list[str], limit: int = 6) -> list[dict[str, Any]]:
    size = 8
    if len(tokens) < size * 2:
        return []
    counts = Counter(
        " ".join(tokens[start : start + size])
        for start in range(len(tokens) - size + 1)
    )
    repeated = [(phrase, count) for phrase, count in counts.items() if count > 1]
    repeated.sort(key=lambda item: (-item[1], -len(item[0])))

    chosen: list[tuple[str, int]] = []
    for phrase, count in repeated:
        if any(phrase in kept for kept, _ in chosen):
            continue
        chosen.append((phrase, count))
        if len(chosen) >= limit:
            break
    return [{"phrase": phrase, "count": count} for phrase, count in chosen]


def check(text: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare ``text`` with reference documents and report local overlaps."""
    input_tokens = _tokens(text)
    input_shingles = _shingles(input_tokens)
    sentences = _sentences(text)
    sentence_sets = [
        (sentence, _shingles(_tokens(sentence), SENTENCE_SHINGLE_SIZE))
        for sentence in sentences
    ]

    matches: list[dict[str, Any]] = []
    if input_shingles:
        for reference in references:
            ref_tokens = _tokens(str(reference.get("content", "")))
            ref_shingles = _shingles(ref_tokens)
            ref_sentence_shingles = _shingles(ref_tokens, SENTENCE_SHINGLE_SIZE)
            if not ref_shingles:
                continue
            shared = input_shingles & ref_shingles
            if not shared:
                continue
            containment = len(shared) / len(input_shingles)
            hits: list[dict[str, Any]] = []
            for sentence, shingles in sentence_sets:
                if not shingles:
                    continue
                overlap = len(shingles & ref_sentence_shingles) / len(shingles)
                if overlap >= SENTENCE_MATCH_THRESHOLD:
                    hits.append(
                        {
                            "sentence": _clip(sentence),
                            "overlap_percent": round(overlap * 100),
                        }
                    )
            if containment >= 0.03 or hits:
                matches.append(
                    {
                        "reference_id": reference.get("id"),
                        "title": str(reference.get("title", "Untitled reference")),
                        "similarity_percent": round(containment * 100),
                        "overlap_words": len(shared) * SHINGLE_SIZE,
                        "excerpt": _clip(str(reference.get("content", ""))),
                        "matched_sentences": hits,
                        "matched_passages": _matched_passages(
                            text, str(reference.get("content", ""))
                        ),
                    }
                )

    matches.sort(key=lambda item: (-int(item["similarity_percent"]), str(item["title"])))

    total_sentences = len(sentences)

    notes: list[str] = []
    if not references:
        notes.append("No reference documents yet. Add your own texts to compare against.")
    if total_sentences == 0:
        notes.append("Add at least a few full sentences for a useful comparison.")
    if input_tokens and len(input_tokens) < 40:
        notes.append("Short passages produce noisy results; 40+ words is more reliable.")

    coverage = 0
    if total_sentences:
        matched_sentences = {
            hit["sentence"] for match in matches for hit in match["matched_sentences"]
        }
        coverage = round(100 * len(matched_sentences) / total_sentences)

    return {
        "local_only": True,
        "disclaimer": DISCLAIMER,
        "word_count": len(input_tokens),
        "sentence_count": total_sentences,
        "checked_references": len(references),
        "coverage_percent": coverage,
        "matches": matches,
        "repeated_phrases": _repeated_phrases(input_tokens),
        "notes": notes,
    }
