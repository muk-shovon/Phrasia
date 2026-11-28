"""Cheap meaning check for one rewritten sentence.

The first test is deterministic: token and bigram cosine similarity. A clear
pass or a clear fail is settled locally. Only the ambiguous middle band asks
the provider for a one-word YES/NO answer, so most sentences cost no extra
call.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from backend.engine.lexicon import NEGATIONS
from backend.engine.llm.prompts import load_prompt

_WORD = re.compile(r"[a-z0-9']+")
_STOP = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "in", "into", "is", "it", "its", "of", "on", "or", "that",
    "the", "their", "them", "this", "to", "was", "were", "will", "with",
}


def _tokens(text: str) -> list[str]:
    return [
        word for word in _WORD.findall((text or "").lower())
        if word not in _STOP
    ]


def _vector(tokens: list[str], size: int) -> Counter[str]:
    return Counter(
        " ".join(tokens[index:index + size])
        for index in range(max(len(tokens) - size + 1, 0))
    )


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def similarity(source: str, candidate: str) -> float:
    """Return a 0–1 blend of unigram and bigram cosine similarity."""
    source_tokens = _tokens(source)
    candidate_tokens = _tokens(candidate)
    unigram = _cosine(_vector(source_tokens, 1), _vector(candidate_tokens, 1))
    bigram = _cosine(_vector(source_tokens, 2), _vector(candidate_tokens, 2))
    return round(unigram * 0.7 + bigram * 0.3, 3)


def _negations(text: str) -> list[str]:
    return sorted(word for word in _WORD.findall((text or "").lower()) if word in NEGATIONS)


def _ask_provider(chain: Any, source: str, candidate: str) -> bool | None:
    if chain is None:
        return None
    from backend.engine import protect

    system = load_prompt("meaning_check_system.md")
    user = load_prompt("meaning_check_user.md")
    masked_source = protect.extract(source)[0]
    masked_candidate = protect.extract(candidate)[0]
    user = user.replace("{source}", masked_source).replace("{candidate}", masked_candidate)
    try:
        completion = chain.complete(system, user, temperature=0.0, max_tokens=6)
    except Exception:
        return None
    answer = (completion.text or "").strip().lower()
    if answer.startswith("yes"):
        return True
    if answer.startswith("no"):
        return False
    return None


def assess(
    chain: Any,
    source: str,
    candidate: str,
    *,
    use_llm: bool = True,
) -> tuple[bool, float, str]:
    """Return ``(ok, score, reason)`` for a candidate rewrite."""
    score = similarity(source, candidate)
    if _negations(source) != _negations(candidate):
        return False, score, "negation_changed"
    if score >= 0.82:
        return True, score, "cosine_pass"
    if score < 0.50:
        return False, score, "cosine_low"
    if use_llm:
        answer = _ask_provider(chain, source, candidate)
        if answer is True:
            return True, score, "llm_yes"
        if answer is False:
            return False, score, "llm_no"
    if score >= 0.62:
        return True, score, "cosine_accept"
    return False, score, "cosine_borderline"
