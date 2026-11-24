"""Local writing-style signal.

This is a readable heuristic, not an authorship classifier. It reports named
signals and a plain-language label, never a percentage verdict.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from typing import Any

from backend.core.chunking import split_sentences

DISCLAIMER = (
    "Local style signal — not proof of authorship. It describes surface patterns "
    "in the text and cannot tell you who wrote it."
)

FORMULAIC_PHRASES = (
    "furthermore",
    "moreover",
    "additionally",
    "in conclusion",
    "it is important to note",
    "it is worth noting",
    "in today's",
    "delve into",
    "delves into",
    "tapestry",
    "landscape of",
    "realm of",
    "testament to",
    "navigate the complexities",
    "in the ever-evolving",
    "plays a crucial role",
    "plays a vital role",
    "a myriad of",
    "underscores the importance",
    "paramount",
)

HEDGES = (
    "arguably",
    "essentially",
    "fundamentally",
    "notably",
    "significantly",
    "substantially",
    "ultimately",
    "various",
    "numerous",
    "plethora",
    "utilize",
    "utilizes",
    "leverage",
    "leverages",
    "facilitate",
    "facilitates",
    "optimal",
    "robust",
    "seamless",
)

CONTRACTIONS = re.compile(
    r"\b(?:it's|that's|don't|doesn't|can't|won't|isn't|aren't|wasn't|weren't|"
    r"i'm|you're|we're|they're|i've|we've|they've|let's|didn't|couldn't|"
    r"wouldn't|shouldn't|there's|here's|what's|who's|n't)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[A-Za-z']+")


def _count_phrases(lowered: str, phrases: tuple[str, ...]) -> tuple[int, list[str]]:
    found: list[str] = []
    total = 0
    for phrase in phrases:
        hits = lowered.count(phrase)
        if hits:
            total += hits
            found.append(phrase)
    return total, found


def _sentence_lengths(sentences: list[str]) -> list[int]:
    return [len(_WORD.findall(sentence)) for sentence in sentences if sentence.strip()]


def _openers(sentences: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for sentence in sentences:
        words = _WORD.findall(sentence)
        if len(words) >= 3:
            counter[" ".join(word.lower() for word in words[:2])] += 1
    return counter


def analyze(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    words = _WORD.findall(cleaned)
    word_count = len(words)
    sentences = [sentence.strip() for sentence in split_sentences(cleaned) if sentence.strip()]
    lowered = cleaned.lower()

    formulaic_total, formulaic_found = _count_phrases(lowered, FORMULAIC_PHRASES)
    hedge_total, hedge_found = _count_phrases(lowered, HEDGES)
    contractions = len(CONTRACTIONS.findall(cleaned))

    per_hundred = (lambda value: (value / word_count * 100) if word_count else 0.0)
    formulaic_rate = per_hundred(formulaic_total)
    hedge_rate = per_hundred(hedge_total)

    lengths = _sentence_lengths(sentences)
    variation = 0.0
    if len(lengths) >= 3:
        mean = statistics.fmean(lengths)
        variation = statistics.pstdev(lengths) / mean if mean else 0.0

    openers = _openers(sentences)
    repeated_opener, repeated_opener_count = ("", 0)
    if openers:
        repeated_opener, repeated_opener_count = openers.most_common(1)[0]

    unique_ratio = len({word.lower() for word in words}) / word_count if word_count else 0.0

    points = 0
    signals: list[dict[str, str]] = []

    if formulaic_total:
        points += 2 if formulaic_rate >= 1.0 else 1
        signals.append(
            {
                "name": "Stock transitions",
                "detail": (
                    f"{formulaic_total} formulaic phrase(s) found, for example: "
                    + ", ".join(f"“{phrase}”" for phrase in formulaic_found[:4])
                    + "."
                ),
                "direction": "formulaic",
            }
        )
    else:
        signals.append(
            {
                "name": "Stock transitions",
                "detail": "No common formulaic transitions detected.",
                "direction": "conversational",
            }
        )

    if hedge_total:
        points += 2 if hedge_rate >= 1.0 else 1
        signals.append(
            {
                "name": "Abstract vocabulary",
                "detail": (
                    f"{hedge_total} abstract or inflated word(s), such as: "
                    + ", ".join(hedge_found[:4])
                    + "."
                ),
                "direction": "formulaic",
            }
        )
    else:
        signals.append(
            {
                "name": "Abstract vocabulary",
                "detail": "Little inflated vocabulary detected.",
                "direction": "conversational",
            }
        )

    if word_count >= 80:
        if contractions == 0:
            points += 1
            signals.append(
                {
                    "name": "Contractions",
                    "detail": "No contractions in a long passage, which can read stiff.",
                    "direction": "formulaic",
                }
            )
        else:
            signals.append(
                {
                    "name": "Contractions",
                    "detail": f"{contractions} contraction(s) used.",
                    "direction": "conversational",
                }
            )

    if repeated_opener_count >= 3:
        points += 1
        signals.append(
            {
                "name": "Repeated sentence openings",
                "detail": (
                    f"{repeated_opener_count} sentences start with “{repeated_opener}”."
                ),
                "direction": "formulaic",
            }
        )
    elif lengths:
        signals.append(
            {
                "name": "Sentence openings",
                "detail": "Sentence openings are varied.",
                "direction": "conversational",
            }
        )

    if len(lengths) >= 3:
        if variation < 0.3:
            points += 1
            signals.append(
                {
                    "name": "Sentence rhythm",
                    "detail": "Sentence lengths are fairly uniform.",
                    "direction": "formulaic",
                }
            )
        else:
            signals.append(
                {
                    "name": "Sentence rhythm",
                    "detail": "Sentence lengths vary noticeably.",
                    "direction": "conversational",
                }
            )

    if word_count >= 120 and unique_ratio < 0.42:
        points += 1
        signals.append(
            {
                "name": "Vocabulary range",
                "detail": "The same words are reused often.",
                "direction": "formulaic",
            }
        )
    elif word_count:
        signals.append(
            {
                "name": "Vocabulary range",
                "detail": "Vocabulary repeats at a normal rate.",
                "direction": "neutral",
            }
        )

    if points >= 4:
        label = "leans formulaic"
        summary = (
            "The passage leans on stock transitions, abstract wording or uniform "
            "rhythm. That is a style note, not a verdict about who wrote it."
        )
    elif points >= 2:
        label = "mixed"
        summary = (
            "The passage mixes natural and formulaic patterns. Editing the flagged "
            "signals would make it read more like a person wrote it."
        )
    else:
        label = "leans conversational"
        summary = (
            "The passage reads mostly like ordinary human prose, with few stock "
            "transitions or uniform rhythms."
        )

    return {
        "label": label,
        "summary": summary,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "signals": signals,
        "disclaimer": DISCLAIMER,
    }
