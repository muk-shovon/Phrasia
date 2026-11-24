"""Our own weighted feature ranker, with weights in data/ranker.json."""
from __future__ import annotations

import difflib
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.engine import plan

DATA = Path(__file__).resolve().parent / "data"
_WEIGHTS_PATH = DATA / "ranker.json"
_PATTERNS_PATH = DATA / "ai_patterns.json"
_LM_PATH = DATA / "lm.json"
_WORD = re.compile(r"[A-Za-z0-9']+")


@lru_cache(maxsize=1)
def config() -> dict[str, Any]:
    return json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))


_OVERRIDES: dict[str, float] = {}


def set_weights(values: dict[str, float]) -> None:
    """Temporarily override weights (used by tune.py)."""
    _OVERRIDES.clear()
    _OVERRIDES.update(values)


def weights() -> dict[str, float]:
    result = dict(config()["weights"])
    result.update(_OVERRIDES)
    return result


@lru_cache(maxsize=1)
def _pattern_rules() -> list[tuple[str, re.Pattern[str]]]:
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for item in json.loads(_PATTERNS_PATH.read_text(encoding="utf-8")):
        raw = str(item.get("pattern", ""))
        if not raw:
            continue
        if item.get("kind") == "regex":
            pattern = raw
        else:
            parts = [part.strip() for part in raw.split("|") if part.strip()]
            if not parts:
                continue
            pattern = r"(?<!\w)(?:" + "|".join(map(re.escape, parts)) + r")(?!\w)"
        try:
            compiled.append((str(item["id"]), re.compile(pattern, re.IGNORECASE | re.MULTILINE)))
        except re.error:
            continue
    return compiled


def pattern_count(text: str) -> int:
    return sum(len(rule.findall(text or "")) for _id, rule in _pattern_rules())


def similarity(source: str, candidate: str) -> float:
    a = [word.lower() for word in _WORD.findall(source)]
    b = [word.lower() for word in _WORD.findall(candidate)]
    return round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 3)


@lru_cache(maxsize=1)
def _lm() -> dict[str, int] | None:
    if not _LM_PATH.is_file():
        return None
    try:
        data = json.loads(_LM_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    counts = data.get("counts")
    return counts if isinstance(counts, dict) else None


def fluency(text: str) -> float:
    counts = _lm()
    if not counts:
        return 0.0
    words = [word.lower() for word in _WORD.findall(text)]
    if len(words) < 3:
        return 0.0
    total = 0.0
    for index in range(2, len(words)):
        first, second, third = words[index - 2:index + 1]
        tri = int(counts.get(f"tri:{first} {second} {third}", 0))
        bi = int(counts.get(f"bi:{first} {second}", 0))
        uni = int(counts.get(f"uni:{first}", 0))
        value = math.log((tri + 1) / (bi + 2)) + math.log((bi + 1) / (uni + 2))
        total += value
    return round(total / max(len(words) - 2, 1), 3)


def features(source: str, candidate: str, *, target: int = 11, previous: str = "", safety: str = "low", restructured: bool = False) -> dict[str, float]:
    source_words = [word.lower() for word in _WORD.findall(source)]
    first_source = " ".join(source_words[:4])
    first_candidate = " ".join(word.lower() for word in _WORD.findall(candidate)[:4])
    ratio = plan.word_count(candidate) / max(plan.word_count(source), 1)
    risk_penalty = config()["risk_penalty"].get(safety, 0.0)
    return {
        "structural_distance": round(1.0 - similarity(source, candidate) + (0.15 if first_source != first_candidate else 0.0), 3),
        "rhythm_fit": plan.rhythm_fit(plan.word_count(candidate), target),
        "pattern_reduction": round(float(pattern_count(source) - pattern_count(candidate)), 3),
        "length_window": 1.0 if 0.8 <= ratio <= 1.2 else 0.0,
        "rule_risk": -float(risk_penalty),
        "repeated_opening": -1.0 if previous and first_candidate.split()[:1] == [str(previous).lower()] else 0.0,
        "fluency": fluency(candidate),
        "status_bonus": 1.0 if restructured else 0.0,
    }


def score(source: str, candidate: str, **context: Any) -> float:
    values = features(source, candidate, **context)
    return round(sum(weights().get(name, 0.0) * value for name, value in values.items()), 4)


def rank(source: str, candidates: list[str], **context: Any) -> list[str]:
    return sorted(candidates, key=lambda item: (-score(source, item, **context), item))
