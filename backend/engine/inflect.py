"""Small, curated English inflections for rule replacements."""
from __future__ import annotations

_IRREGULAR = {
    "make": ("makes", "made", "making"),
    "take": ("takes", "took", "taking"),
    "give": ("gives", "gave", "giving"),
    "conduct": ("conducts", "conducted", "conducting"),
    "provide": ("provides", "provided", "providing"),
    "decide": ("decides", "decided", "deciding"),
    "look": ("looks", "looked", "looking"),
    "try": ("tries", "tried", "trying"),
    "analyze": ("analyzes", "analyzed", "analyzing"),
    "support": ("supports", "supported", "supporting"),
    "be": ("is", "was", "being"),
    "have": ("has", "had", "having"),
    "do": ("does", "did", "doing"),
}
_NOUN_IRREGULAR = {"person": "people", "child": "children", "analysis": "analyses", "decision": "decisions"}


def _clean(word: str) -> str:
    return "".join(character for character in (word or "").lower() if character.isalpha())


def third_person(word: str) -> str:
    value = _clean(word)
    if value in _IRREGULAR:
        return _IRREGULAR[value][0]
    if value.endswith(("s", "x", "ch", "sh")):
        return value + "es"
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ies"
    return value + "s"


def past(word: str) -> str:
    value = _clean(word)
    if value in _IRREGULAR:
        return _IRREGULAR[value][1]
    if value.endswith("e"):
        return value + "d"
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ied"
    return value + "ed"


def ing(word: str) -> str:
    value = _clean(word)
    if value in _IRREGULAR:
        return _IRREGULAR[value][2]
    if value.endswith("e"):
        return value[:-1] + "ing"
    return value + "ing"


def plural(word: str) -> str:
    value = _clean(word)
    if value in _NOUN_IRREGULAR:
        return _NOUN_IRREGULAR[value]
    if value.endswith(("s", "x", "ch", "sh")):
        return value + "es"
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ies"
    return value + "s"


def adverb(word: str) -> str:
    value = _clean(word)
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ily"
    if value.endswith("le"):
        return value[:-1] + "y"
    return value + "ly"


def base(word: str) -> str:
    value = _clean(word)
    for base_form, forms in _IRREGULAR.items():
        if value == base_form or value in forms:
            return base_form
    if value.endswith("ies"):
        return value[:-3] + "y"
    if value.endswith("ing"):
        return value[:-3]
    if value.endswith("ed"):
        return value[:-2]
    if value.endswith("es"):
        return value[:-2]
    if value.endswith("s"):
        return value[:-1]
    return value


def form_of(target: str, source_word: str) -> str:
    """Inflect ``target`` to match the surface form of ``source_word``."""
    lowered = (source_word or "").lower()
    if lowered.endswith("ing"):
        return ing(target)
    if lowered.endswith("ed"):
        return past(target)
    if lowered.endswith("ies"):
        return third_person(target)
    if lowered.endswith("s") and not lowered.endswith("ss"):
        return third_person(target)
    return target
