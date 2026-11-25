"""Meaning, content and grammar checks against the source sentence only."""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from backend.engine import sentences
from backend.engine.lexicon import (
    CONNECTIVES, COORDINATORS, HEDGES, NEGATIONS, PHRASE_EQUIVALENCE, PRONOUNS,
    DETERMINERS, SUBORDINATORS, guess, is_content,
)

_EQUIVALENCE: tuple[tuple[str, ...], ...] = (
    ("no", "zero", "none"),
    ("only", "just"),
    ("can", "is able to", "able to"),
    ("but", "yet", "however"),
    ("because", "since", "as"),
    ("may", "might"),
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"']+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PLACEHOLDER = re.compile(r"\[PHRASIA_[A-Z_]+\d*\]")
_WORD = re.compile(r"[A-Za-z0-9']+")
_NAME = re.compile(r"\b[A-Z][A-Za-z]+\b")
_NAME_STOP = {
    "A", "An", "At", "Because", "For", "From", "Fundamentally", "He", "Heads",
    "Here", "Honestly", "However", "I", "In", "It", "Its", "Let", "Look", "No", "Now",
    "Overall", "Quick", "Real", "She", "That", "The", "Their", "There", "These", "They",
    "This", "Those", "Through", "To", "Ultimately", "We", "When", "Where", "While",
    "With", "Without", "You",
}
_DOUBLE = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
_TERMINAL = re.compile(r"[.!?…][\"'”’)\]]*$")
_WORDS_PATH = Path(__file__).resolve().parent / "data" / "words.json"
_CONTENT_THRESHOLD = 0.9
_LENGTH_MIN = 0.8
_LENGTH_MAX = 1.2
_EDIT_NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:serves|stands|functions|operates)\s+as\b", re.I), "is"),
    (re.compile(r"\b(?:served|stood|functioned|operated)\s+as\b", re.I), "was"),
    (re.compile(r"\b(?:boasts|features|offers|maintains)\b", re.I), "has"),
    (re.compile(r"\bthe real question is\b", re.I), "the question is"),
    (re.compile(r"\bwhat really matters is\b", re.I), "what matters is"),
    (re.compile(r"\bthe deeper issue is\b", re.I), "the issue is"),
    (re.compile(r"\b(?:could potentially)\b", re.I), "could"),
    (re.compile(r"\b(?:might arguably)\b", re.I), "might"),
    (re.compile(r"\b(?:may possibly)\b", re.I), "may"),
    (re.compile(r"\bnestled (?:within|in)\b", re.I), "in"),
    (re.compile(r"\bin the heart of\b", re.I), "in"),
    (re.compile(r"\brenowned\b", re.I), "well known"),
    (re.compile(r"\bexemplifies\b", re.I), "shows"),
)


@lru_cache(maxsize=1)
def _banned_map() -> tuple[tuple[str, str], ...]:
    data = json.loads(_WORDS_PATH.read_text(encoding="utf-8"))
    return tuple((str(item["word"]), str(item["replacement"])) for item in data)


def _normalise(text: str) -> str:
    result = text or ""
    result = re.sub(
        r"\bno\s+([A-Za-z][\w -]{1,50}?)\s+(?:is\s+|are\s+)?needed\b",
        r"not need \1",
        result,
        flags=re.IGNORECASE,
    )
    for pattern, replacement in _EDIT_NORMALIZATIONS:
        result = pattern.sub(replacement, result)
    for banned, replacement in _banned_map():
        if not replacement:
            result = re.sub(r"(?<!\w)" + re.escape(banned) + r"(?!\w)", "", result, flags=re.IGNORECASE)
            continue
        if banned == replacement:
            continue
        pattern = r"(?<!\w)(?:" + re.escape(banned) + "|" + re.escape(replacement) + r")(?!\w)"
        result = re.sub(pattern, replacement.lower(), result, flags=re.IGNORECASE)
    for group in (*_EQUIVALENCE, *PHRASE_EQUIVALENCE):
        canonical = group[0]
        for phrase in group[1:]:
            result = re.sub(
                r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                canonical,
                result,
                flags=re.IGNORECASE,
            )
    return result


def _words(text: str) -> list[str]:
    return [word.lower() for word in _WORD.findall(text or "")]


def _counts(items: list[str]) -> Counter[str]:
    return Counter(items)


def preserve_critical(source: str, candidate: str) -> bool:
    """Numbers, names, URLs, placeholders, hedges and negations must survive."""
    source_n = _normalise(source)
    candidate_n = _normalise(candidate)
    for number in _NUMBER.findall(source_n):
        if number not in _NUMBER.findall(candidate_n):
            return False
    for match in _NAME.finditer(source):
        if match.group(0) in _NAME_STOP:
            continue
        prefix = source[:match.start()].rstrip()
        at_sentence_start = not prefix or prefix.endswith((".", "!", "?", "\n"))
        if at_sentence_start and re.search(
            rf"(?<!\w){re.escape(match.group(0))}(?!\w)", candidate, re.IGNORECASE
        ):
            continue
        if match.group(0) not in candidate:
            return False
    for url in _URL.findall(source):
        if url not in candidate:
            return False
    for placeholder in _PLACEHOLDER.findall(source):
        if placeholder not in candidate:
            return False
    src_words = _counts(_words(source_n))
    out_words = _counts(_words(candidate_n))
    for word in HEDGES | NEGATIONS:
        if src_words.get(word, 0) > out_words.get(word, 0):
            return False
    return True


def _remove_exemptions(source: str, dropped_by_rule: Iterable[str]) -> str:
    result = source
    for dropped in dropped_by_rule:
        if not dropped:
            continue
        start = result.find(dropped)
        if start >= 0:
            result = result[:start] + result[start + len(dropped):]
            continue
        result = re.sub(re.escape(dropped), "", result, count=1, flags=re.IGNORECASE)
    return result


def content_retention(
    source: str,
    candidate: str,
    *,
    dropped_by_rule: Iterable[str] = (),
) -> float:
    """Fraction of source content words still present in the candidate."""
    source = _remove_exemptions(source, dropped_by_rule)
    src = [word for word in _words(_normalise(source)) if is_content(word)]
    out = _counts(_words(_normalise(candidate)))
    if not src:
        return 1.0
    kept = sum(min(count, out.get(word, 0)) for word, count in _counts(src).items())
    return round(kept / len(src), 3)


def grammar_sanity(text: str) -> bool:
    """Basic grammar checks, including subjects after a sentence split."""
    value = (text or "").strip()
    if not value:
        return False
    if value.count('"') % 2 or value.count("“") != value.count("”"):
        return False
    for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
        if value.count(opening) != value.count(closing):
            return False
    first = value[0]
    if not (first.isupper() or first.isdigit() or first in "\"“'([{"):
        return False
    if not _TERMINAL.search(value):
        return False
    if _DOUBLE.search(value):
        return False
    tokens = _words(value)
    if not tokens:
        return False
    if tokens[0] in COORDINATORS or tokens[-1] in COORDINATORS | SUBORDINATORS:
        return False
    parts = sentences.texts(value)
    if len(parts) > 1:
        for part in parts:
            words = _words(part)
            raw_words = _WORD.findall(part)
            if not words:
                return False
            subject = any(
                word in PRONOUNS or word in DETERMINERS or guess(word) == "noun"
                or (raw_word[:1].isupper() and word not in CONNECTIVES)
                for word, raw_word in zip(words[:8], raw_words[:8])
            )
            if not subject:
                return False
    return True


def length_ratio(source: str, candidate: str) -> float:
    """Word-count ratio of candidate to source."""
    source_len = max(len(_words(source)), 1)
    return round(len(_words(candidate)) / source_len, 3)


def validate(
    source: str,
    candidate: str,
    *,
    dropped_by_rule: Iterable[str] = (),
    length_min: float = _LENGTH_MIN,
    length_max: float = _LENGTH_MAX,
) -> tuple[bool, list[str]]:
    """Return (ok, reasons) for a candidate rewrite of one source unit."""
    reasons: list[str] = []
    if not preserve_critical(source, candidate):
        reasons.append("critical")
    if content_retention(source, candidate, dropped_by_rule=dropped_by_rule) < _CONTENT_THRESHOLD:
        reasons.append("content")
    if not grammar_sanity(candidate):
        reasons.append("grammar")
    ratio = length_ratio(source, candidate)
    if ratio < length_min or ratio > length_max:
        reasons.append("length")
    return (not reasons), reasons


def details(source: str, candidate: str) -> dict[str, Any]:
    """Human-readable diagnostic for local debugging."""
    ok, reasons = validate(source, candidate)
    return {
        "ok": ok,
        "reasons": reasons,
        "content_retention": content_retention(source, candidate),
        "length_ratio": length_ratio(source, candidate),
    }
