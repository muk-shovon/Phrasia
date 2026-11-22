"""Local, offline AI-writing detector used for Phrasia's Deep Scan.

StealthWriter exposes a per-sentence score with a 0.5 "looks human" threshold
(observed in its shipped client). Phrasia uses the same presentation model but
a transparent, deterministic heuristic — no external detector is called and no
text leaves the machine for scoring.

The score is a *writing-style signal*, not a verdict about authorship.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

HUMAN_THRESHOLD = 0.5

_STOCK_OPENERS = (
    "furthermore", "moreover", "additionally", "in conclusion", "in summary",
    "overall", "it is important to note", "it is worth noting", "that being said",
    "in today's", "in the modern world", "with the advent of",
)

_AI_PHRASES = (
    "it is important to note", "it is worth noting", "it should be noted",
    "in order to", "due to the fact that", "a wide range of", "a large number of",
    "plays a crucial role", "has become an integral part", "when it comes to",
    "on the other hand", "in conclusion", "furthermore", "moreover", "additionally",
)

_AI_WORDS = (
    "delve", "tapestry", "testament", "realm", "landscape", "crucial", "pivotal",
    "vital", "robust", "seamless", "foster", "leverage", "utilize", "utilization",
    "navigate", "underscore", "comprehensive", "multifaceted", "ever-evolving",
    "advancements", "integral", "significant", "essential", "facilitate",
    "facilitated", "innovation", "domain", "domains",
)

_CONTRACTION = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class SentenceScore:
    id: int
    sentence: str
    score: float
    reasons: list[str]

    @property
    def looks_human(self) -> bool:
        return self.score >= HUMAN_THRESHOLD

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sentence": self.sentence,
            "score": round(self.score, 4),
            "score_pct": round(self.score * 100),
            "looks_human": self.looks_human,
            "reasons": self.reasons,
        }


@dataclass
class ScanResult:
    normal_score: float
    sentences: list[SentenceScore]

    @property
    def looks_human(self) -> bool:
        return self.normal_score >= HUMAN_THRESHOLD

    @property
    def verdict(self) -> str:
        return "Looks Human" if self.looks_human else "AI Detected"

    def as_dict(self) -> dict[str, Any]:
        return {
            "normal_score": round(self.normal_score, 4),
            "verdict": "Looks Human" if self.looks_human else "AI Detected",
            "sentences": [s.as_dict() for s in self.sentences],
        }


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def score_sentence(sentence: str, sentence_id: int = 0) -> SentenceScore:
    text = sentence.strip()
    if not text:
        return SentenceScore(sentence_id, "", 1.0, [])

    low = text.lower()
    words = _words(text)
    n = len(words)
    score = 1.0
    reasons: list[str] = []

    for opener in _STOCK_OPENERS:
        if low.startswith(opener):
            score -= 0.22
            reasons.append(f"stock opener: {opener}")
            break

    hits = [p for p in _AI_PHRASES if p in low]
    if hits:
        score -= min(0.26, 0.09 * len(hits))
        reasons.append("stock transition phrases")

    word_hits = [w for w in _AI_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]
    if word_hits:
        score -= min(0.26, 0.055 * len(word_hits))
        reasons.append("abstract/buzzword vocabulary")

    if n >= 9 and not _CONTRACTION.search(text):
        score -= 0.05
        reasons.append("no natural contractions")

    if 18 <= n <= 32:
        score -= 0.04
        reasons.append("uniform mid-length sentence")

    if re.search(r"\b(?:has been|have been|is being|are being|was|were)\b", low):
        score -= 0.04
        reasons.append("passive construction")

    # Human-writing signals.
    if _CONTRACTION.search(text):
        score += 0.06
        reasons.append("natural contractions")
    if n <= 8:
        score += 0.06
        reasons.append("short sentence")
    if "—" in text or "(" in text:
        score += 0.03
        reasons.append("natural aside")
    if re.search(r"\b(?:I|you|we|your|our)\b", text):
        score += 0.02
        reasons.append("direct voice")

    score = max(0.02, min(0.99, score))
    return SentenceScore(sentence_id, text, round(score, 4), reasons)


def scan(text: str) -> ScanResult:
    """Score a whole passage, weighting longer sentences slightly more."""
    if not text or not text.strip():
        return ScanResult(1.0, [])
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    if not parts:
        parts = [text.strip()]
    sentences = [score_sentence(part, i) for i, part in enumerate(parts)]
    weights = [max(4, len(_words(s.sentence))) for s in sentences]
    total = sum(s.score * w for s, w in zip(sentences, weights))
    normal = total / sum(weights)
    return ScanResult(round(normal, 4), sentences)
