"""Sentence analysis and the seven allowed rewrite operations.

The planner never invents an operation outside this list:

``synonym``  swap a word or phrase
``clause``   move a clause, keeping every idea
``split``    turn one long sentence into two
``merge``    join two short adjacent sentences
``opening``  replace a repeated or staged opener
``punchy``   make a long, loose sentence short and direct
``keep``     leave the sentence almost untouched
"""
from __future__ import annotations

import hashlib
import re
import statistics
from dataclasses import dataclass, field
from typing import Any

from backend.engine.lexicon import HEDGES, NEGATIONS, PRONOUNS
from backend.engine.skill import scan as skill_scan

OPERATIONS = ("synonym", "clause", "split", "merge", "opening", "punchy", "keep")

LABELS = {
    "synonym": "Word and phrase swap",
    "clause": "Clause reorder",
    "split": "Split into two",
    "merge": "Merge with next",
    "opening": "New opening",
    "punchy": "Short and direct",
    "keep": "Nearly unchanged",
}

INSTRUCTIONS = {
    "synonym": "Replace a predictable word, phrase or stock transition with a plainer, more specific choice.",
    "clause": "Move one clause or phrase inside the sentence. Keep every fact and every idea.",
    "split": "Divide the sentence into two complete sentences. The meaning must not change.",
    "merge": "Join the pair into one complete sentence without dropping any detail.",
    "opening": "Write a different opening for this sentence. Do not add a new claim.",
    "punchy": "Make this sentence shorter and more direct. Keep the same meaning.",
    "keep": "Return the sentence almost unchanged.",
}

_QUANTIFIERS = {
    "all", "always", "any", "both", "each", "every", "few", "many", "much",
    "never", "none", "often", "several", "some", "usually", "various", "very",
}
_CLAUSE_BREAK = re.compile(
    r";|,\s*(?:and|but|which|who|while|because|although|though|whereas)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"[A-Za-z0-9']+")


def _seed(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)


def words(text: str) -> int:
    return len(_WORD.findall(text or ""))


def opening(text: str) -> str:
    match = _WORD.search(text or "")
    return match.group(0).lower() if match else ""


def bucket(length: int) -> str:
    if length <= 10:
        return "short"
    if length <= 24:
        return "medium"
    return "long"


@dataclass
class SentenceInfo:
    index: int
    text: str
    length: int
    opening: str
    bucket: str
    hits: int
    hedge: int
    quantifier: int
    pronoun: int
    reason: str = ""
    operation: str = "keep"
    paired: bool = False


@dataclass
class TextAnalysis:
    sentences: list[SentenceInfo] = field(default_factory=list)
    average_length: float = 0.0
    burstiness: float = 0.0
    repeated_openings: int = 0
    hedge_density: float = 0.0
    quantifier_density: float = 0.0
    pronoun_ratio: float = 0.0
    pattern_hits: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "sentences": len(self.sentences),
            "average_length": round(self.average_length, 1),
            "burstiness": round(self.burstiness, 1),
            "repeated_openings": self.repeated_openings,
            "hedge_density": round(self.hedge_density, 2),
            "quantifier_density": round(self.quantifier_density, 2),
            "pronoun_ratio": round(self.pronoun_ratio, 2),
            "pattern_hits": self.pattern_hits,
            "length_mix": {
                key: sum(1 for item in self.sentences if item.bucket == key)
                for key in ("short", "medium", "long")
            },
        }


def analyze(texts: list[str], options: dict[str, Any] | None = None) -> TextAnalysis:
    infos: list[SentenceInfo] = []
    for index, value in enumerate(texts, start=1):
        cleaned = (value or "").strip()
        length = words(cleaned)
        lowered = cleaned.lower()
        tokens = _WORD.findall(lowered)
        hits = len(skill_scan.scan(cleaned, options, gated=False)) if cleaned else 0
        infos.append(
            SentenceInfo(
                index=index,
                text=cleaned,
                length=length,
                opening=opening(cleaned),
                bucket=bucket(length),
                hits=hits,
                hedge=sum(1 for token in tokens if token in HEDGES),
                quantifier=sum(1 for token in tokens if token in _QUANTIFIERS),
                pronoun=sum(1 for token in tokens if token in PRONOUNS),
            )
        )
    lengths = [item.length for item in infos] or [0]
    openings = [item.opening for item in infos if item.opening]
    total_words = max(sum(lengths), 1)
    analysis = TextAnalysis(
        sentences=infos,
        average_length=sum(lengths) / max(len(lengths), 1),
        burstiness=statistics.pstdev(lengths) if len(lengths) > 1 else 0.0,
        repeated_openings=len(openings) - len(set(openings)),
        hedge_density=sum(item.hedge for item in infos) * 100 / total_words,
        quantifier_density=sum(item.quantifier for item in infos) * 100 / total_words,
        pronoun_ratio=sum(item.pronoun for item in infos) / total_words,
        pattern_hits=sum(item.hits for item in infos),
    )
    return analysis


def _keep_share(intensity: str) -> int:
    return {"light": 72, "medium": 60, "heavy": 45, "ninja": 32}.get(
        (intensity or "").strip().lower(), 60
    )


def plan(
    analysis: TextAnalysis,
    *,
    intensity: str = "medium",
    variation: int = 0,
    paragraph_breaks: set[int] | None = None,
) -> list[SentenceInfo]:
    """Assign one operation per sentence, merging adjacent short pairs."""
    breaks = paragraph_breaks or set()
    infos = analysis.sentences
    previous_opening = ""
    previous_operation = ""
    for position, info in enumerate(infos):
        if info.paired or info.length == 0:
            continue
        dice = _seed(info.text, intensity, str(variation), str(info.index)) % 100
        next_info = infos[position + 1] if position + 1 < len(infos) else None
        can_merge = (
            next_info is not None
            and not next_info.paired
            and (position + 1) not in breaks
            and info.length <= 12
            and next_info.length <= 14
            and info.hits + next_info.hits > 0
        )

        if info.length <= 5:
            operation, reason = "keep", "short sentence kept as written"
        elif can_merge and dice % 3 == 0:
            operation, reason = "merge", "two short sentences can share one subject"
            info.paired = True
            next_info.paired = True
        elif info.length > 28 and _CLAUSE_BREAK.search(info.text):
            operation, reason = "split", "long sentence with a clause boundary"
        elif info.opening and info.opening == previous_opening:
            operation, reason = "opening", "repeated opening"
        elif info.hits >= 2 and info.length > 18:
            operation, reason = "punchy", "several pattern hits in a long sentence"
        elif info.hits:
            operation, reason = "synonym", "stock wording or phrase can be swapped"
        elif info.length > 22 and dice % 4 == 0:
            operation, reason = "clause", "long sentence can move one clause"
        elif dice >= _keep_share(intensity):
            operation, reason = "synonym", "light touch for rhythm and variety"
        else:
            operation, reason = "keep", "already close to natural"
            if previous_operation in {"keep", "keep"} and dice < 20:
                operation, reason = "opening", "break a run of similar openings"

        if operation == "merge":
            # The pair is rewritten once. The next sentence is skipped later.
            next_info.operation = "merge"
        info.operation = operation
        info.reason = reason
        previous_opening = info.opening
        previous_operation = operation

    if infos and all(item.operation == "keep" for item in infos if not item.paired):
        target = next((item for item in infos if item.length > 0), None)
        if target is not None:
            target.operation = "synonym"
            target.reason = "light touch so the passage is not returned untouched"
    return infos


def instruction(operation: str) -> str:
    return INSTRUCTIONS.get(operation, INSTRUCTIONS["keep"])


def label(operation: str) -> str:
    return LABELS.get(operation, LABELS["keep"])
