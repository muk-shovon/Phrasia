"""Data-driven, deterministic transform library."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from backend.engine import inflect, synonyms, tones
from backend.engine.lexicon import COORDINATORS, SUBORDINATORS

DATA = Path(__file__).resolve().parent / "data"
_RULES_PATH = DATA / "rules.json"
_PHRASES_PATH = DATA / "phrases.json"
_LEAD = re.compile(r"^(When|Although|Because|Even when|Through|With|Using|In)\b([^,]{0,90}),\s+(.+)$")
_FRONT_ADVERB = re.compile(r"^(.{4,80}?)\s+(also|still|often|usually)\s+(.{3,})$")
_RELATIVE = re.compile(r"^(.{4,90}?)\s+where\s+(.{4,90})$")
_TAIL = re.compile(r"^(.+?),\s+(so|while)\s+(.+)$")
_SOME = re.compile(r"^Some\s+(.+?),\s+while\s+others\s+(.+)$")
_SPLIT = re.compile(r"^(.+?),\s+(so|while|but)\s+(.+)$|^([^;]+);\s*(.+)$")
_PASSIVE_NEEDED = re.compile(
    r"^No\s+([A-Za-z][\w -]{1,50}?)\s+(?:is\s+|are\s+)?needed([.!?])$",
    re.IGNORECASE,
)
_TRIAD = re.compile(
    r"^(.{0,80}?[A-Za-z][\w' -]{0,30}),\s+([A-Za-z][\w' -]{0,30}),\s+"
    r"and\s+([A-Za-z][\w' -]{0,30})([.!?])$",
    re.IGNORECASE,
)
_RESTATED_CONTRAST = re.compile(
    r"^(?:It|This|That)(?:'s| is)\s+not\s+(?P<negative>[^,;.!?]{2,70})[,;]\s*"
    r"(?P<positive>(?:it|this|that)(?:'s| is)\s+[^.!?]{2,90})(?P<stop>[.!?])$",
    re.IGNORECASE,
)
_PHRASE_VERBS = {
    "make a decision": "decide", "makes a decision": "decides",
    "made a decision": "decided", "making a decision": "deciding",
    "take a look": "look", "takes a look": "looks", "took a look": "looked",
    "conduct an analysis": "analyze", "conducted an analysis": "analyzed",
    "provide support": "support", "provided support": "supported",
}
_BRIDGES = {"so": "That means", "while": "Still", "but": "Still"}
_CONTRACTIONS = {
    "is not": "isn't", "are not": "aren't", "was not": "wasn't", "were not": "weren't",
    "cannot": "can't", "do not": "don't", "does not": "doesn't", "did not": "didn't",
    "it is": "it's", "they are": "they're", "we are": "we're", "you are": "you're",
}


@lru_cache(maxsize=1)
def rules() -> list[dict[str, Any]]:
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def phrases() -> list[dict[str, Any]]:
    return json.loads(_PHRASES_PATH.read_text(encoding="utf-8"))["phrases"]


def _soften(text: str) -> str:
    text = text.rstrip(".")
    match = re.match(r"^([A-Za-z]+)(.*)$", text)
    if not match:
        return text
    word, rest = match.group(1), match.group(2)
    if word.lower() in COORDINATORS | SUBORDINATORS or word.lower() in {"that", "this", "these", "those"}:
        return word + rest
    if word[:1].isupper() and word.lower() not in {w.lower() for w in _PHRASE_VERBS}:
        return word[0].lower() + word[1:] + rest
    return word + rest


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def move_lead_to_end(sentence: str, **_: Any) -> list[str]:
    match = _LEAD.match(sentence.strip())
    if not match:
        return []
    connector, detail, main = match.groups()
    if _word_count(detail) > 10:
        return []
    phrase = (connector + detail).strip().lower()
    if connector.lower() == "even when":
        phrase = "even when" + detail.lower()
    body = main.rstrip(".")
    body = body[:1].upper() + body[1:]
    return [f"{body} {phrase}."]


def front_adverb(sentence: str, **_: Any) -> list[str]:
    match = _FRONT_ADVERB.match(sentence.strip())
    if not match:
        return []
    main, adverb, tail = match.groups()
    return [f"{adverb.capitalize()}, {_soften(main)} {_soften(tail)}."]


def move_relative_to_front(sentence: str, **_: Any) -> list[str]:
    match = _RELATIVE.match(sentence.strip())
    if not match:
        return []
    main, relative = match.groups()
    if _word_count(main) < 3 or _word_count(relative) < 3:
        return []
    return [f"Where {_soften(relative)}, {_soften(main)}."]


def move_tail_to_front(sentence: str, **_: Any) -> list[str]:
    match = _TAIL.match(sentence.strip())
    if not match:
        return []
    main, marker, tail = match.groups()
    if _word_count(main) < 2 or _word_count(tail) < 3:
        return []
    if marker.lower() == "so":
        return [f"Because {_soften(main)}, {tail.rstrip('.')}."]
    return [f"While {_soften(tail)}, {_soften(main)}."]


def split_bridge(sentence: str, **_: Any) -> list[str]:
    match = _SPLIT.match(sentence.strip())
    if not match:
        return []
    if match.group(1):
        main, marker, tail = match.group(1), match.group(2), match.group(3)
        bridge = _BRIDGES[marker.lower()]
        return [f"{main.strip().rstrip('.')}. {bridge} {_soften(tail)}."]
    main, tail = match.group(4), match.group(5)
    return [f"{main.strip().rstrip('.')}. {_soften(tail)}."]


def some_others_split(sentence: str, **_: Any) -> list[str]:
    match = _SOME.match(sentence.strip())
    if not match:
        return []
    first, second = match.groups()
    return [f"Some {first.rstrip('.')}. Others {_soften(second)}."]


def merge_shared_subject(sentence: str, **context: Any) -> list[str]:
    nxt = str(context.get("next") or "").strip()
    if not nxt:
        return []
    current = sentence.strip().rstrip(".")
    follow = nxt.rstrip(".")
    if _word_count(current) > 14 or _word_count(follow) > 14:
        return []
    first_current = current.split()[:1]
    first_next = follow.split()[:1]
    if not first_current or not first_next or first_current[0].lower() != first_next[0].lower():
        return []
    if first_current[0].lower() in COORDINATORS | SUBORDINATORS:
        return []
    return [f"{current} and {_soften(follow)}."]


def passive_needed(sentence: str, **_: Any) -> list[str]:
    match = _PASSIVE_NEEDED.match(sentence.strip())
    if not match:
        return []
    subject, stop = match.groups()
    value = subject.lower().strip()
    if not value.startswith(("a ", "an ", "any ", "the ")) and not value.endswith("s"):
        article = "an" if value[:1] in "aeiou" else "a"
        value = f"{article} {value}"
    return [f"You do not need {value}{stop}"]


def triad(sentence: str, **_: Any) -> list[str]:
    """Offer a low-priority triad reshaping when no protected fact is present."""
    match = _TRIAD.match(sentence.strip())
    if not match:
        return []
    first, second, third, stop = match.groups()
    if any(re.search(r"\d|https?://|\[PHRASIA_|\b[A-Z]{2,}", item) for item in (first, second, third)):
        return []
    if any(len(item.split()) > 7 for item in (first, second, third)):
        return []
    return [f"{first} and {second}, plus {third}{stop}"]


def contrast_restatement(sentence: str, **_: Any) -> list[str]:
    match = _RESTATED_CONTRAST.match(sentence.strip())
    if not match:
        return []
    negative = set(re.findall(r"[a-z]+", match.group("negative").lower()))
    positive_text = re.sub(r"^(?:it|this|that)(?:'s| is)\s+", "", match.group("positive"), flags=re.I)
    positive = set(re.findall(r"[a-z]+", positive_text.lower()))
    if not negative or not positive or len(negative & positive) / min(len(negative), len(positive)) < 0.6:
        return []
    clause = match.group("positive")
    return [f"{clause[:1].upper()}{clause[1:]}{match.group('stop')}"]


def noun_phrase_verb(sentence: str, **_: Any) -> list[str]:
    results: list[str] = []
    for phrase, replacement in _PHRASE_VERBS.items():
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
        match = pattern.search(sentence)
        if match:
            form = inflect.form_of(replacement, match.group(0))
            results.append(sentence[:match.start()] + form + sentence[match.end():])
            break
    return results


def opener(sentence: str, **_: Any) -> list[str]:
    results: list[str] = []
    for item in phrases():
        if item["position"] not in {"opening", "anywhere"} or not item["replacement"]:
            continue
        phrase = item["phrase"]
        pattern = re.compile(r"^(?:" + re.escape(phrase) + r")\s*,?\s*", re.IGNORECASE)
        match = pattern.match(sentence.strip())
        if match:
            rest = sentence.strip()[match.end():]
            results.append(rest[:1].upper() + rest[1:])
            break
    return results


def connective(sentence: str, **_: Any) -> list[str]:
    results: list[str] = []
    for word in ("moreover", "furthermore", "additionally", "however", "consequently"):
        pattern = re.compile(r"(?<!\w)" + word + r"(?!\w)\s*,?\s*", re.IGNORECASE)
        match = pattern.search(sentence)
        if match:
            replacement = "" if word != "however" else "still"
            results.append(sentence[:match.start()] + replacement + sentence[match.end():])
            break
    return results


def contraction(sentence: str, *, tone: str = "casual", **_: Any) -> list[str]:
    enable = tone in tones.contraction_tones()
    pairs = _CONTRACTIONS if enable else {value: key for key, value in _CONTRACTIONS.items()}
    for source, target in pairs.items():
        pattern = re.compile(r"(?<!\w)" + re.escape(source) + r"(?!\w)", re.IGNORECASE)
        match = pattern.search(sentence)
        if match:
            return [sentence[:match.start()] + target + sentence[match.end():]]
    return []


def _replace_phrase(sentence: str, item: dict[str, Any]) -> str | None:
    phrase = item["phrase"]
    replacement = item["replacement"]
    position = item["position"]
    if position == "opening":
        pattern = re.compile(r"^(?:" + re.escape(phrase) + r")\b\s*,?\s*", re.IGNORECASE)
        match = pattern.match(sentence.strip())
        if not match:
            return None
        text = sentence[match.end():]
        text = text.lstrip(" ,")
        if not replacement:
            return text[:1].upper() + text[1:]
        return replacement + " " + text
    if position == "closing":
        pattern = re.compile(r"\s*,?\s*(?:" + re.escape(phrase) + r")\s*[.!?…]*$", re.IGNORECASE)
        match = pattern.search(sentence)
        if not match:
            return None
        return sentence[:match.start()] + (replacement + "." if replacement else ".")
    pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
    match = pattern.search(sentence)
    if not match:
        return None
    return sentence[:match.start()] + replacement + sentence[match.end():]


def phrase_swap(sentence: str, **_: Any) -> list[str]:
    for item in phrases():
        candidate = _replace_phrase(sentence, item)
        if candidate and candidate != sentence:
            return [candidate]
    return []


def synonym(sentence: str, *, seed: str = "", **_: Any) -> list[str]:
    candidate = synonyms.replace_sentence(sentence, sha256(seed.encode("utf-8")).hexdigest())
    return [candidate] if candidate != sentence else []


_TRANSFORMS: dict[str, Callable[..., list[str]]] = {
    "move_lead_to_end": move_lead_to_end,
    "front_adverb": front_adverb,
    "move_relative_to_front": move_relative_to_front,
    "move_tail_to_front": move_tail_to_front,
    "split_bridge": split_bridge,
    "some_others_split": some_others_split,
    "merge_shared_subject": merge_shared_subject,
    "passive_needed": passive_needed,
    "triad": triad,
    "contrast_restatement": contrast_restatement,
    "noun_phrase_verb": noun_phrase_verb,
    "opener": opener,
    "connective": connective,
    "contraction": contraction,
    "phrase_swap": phrase_swap,
    "synonym": synonym,
}


def available(*, strength: str, tone: str) -> list[dict[str, Any]]:
    return [
        rule for rule in rules()
        if strength in rule["strengths"] and tone in rule["tones"]
    ]


def apply(rule: dict[str, Any], sentence: str, **context: Any) -> list[str]:
    transform = _TRANSFORMS[rule["transform"]]
    return [
        candidate for candidate in transform(sentence, **context)
        if candidate and candidate.strip() and candidate.strip() != sentence.strip()
    ]
