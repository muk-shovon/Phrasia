"""Curated POS-safe synonym replacement with density caps."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from backend.engine import inflect, sentences

DATA = Path(__file__).resolve().parent / "data" / "synonyms.json"
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _choice(options: list[str], seed: str) -> str:
    return options[int(sha256(seed.encode("utf-8")).hexdigest(), 16) % len(options)]


def replace_sentence(sentence: str, seed: str) -> str:
    config = data()
    cap = int(config["density_cap_per_sentence"])
    used = 0

    def sub(match: re.Match[str]) -> str:
        nonlocal used
        word = match.group(0)
        entry = config["entries"].get(word.lower())
        if not entry or used >= cap:
            return word
        replacement = _choice(list(entry["replacements"]), seed + word.lower())
        replacement = inflect.form_of(replacement, word)
        if word[:1].isupper():
            replacement = replacement[:1].upper() + replacement[1:]
        used += 1
        return replacement

    return _WORD.sub(sub, sentence)


def replace(text: str, seed: str) -> str:
    """Replace at most the per-paragraph cap across each paragraph."""
    config = data()
    paragraph_cap = int(config["density_cap_per_paragraph"])
    result: list[str] = []
    for paragraph in re.split(r"(\n\s*\n)", text):
        if not paragraph.strip():
            result.append(paragraph)
            continue
        parts = sentences.split(paragraph)
        total = 0
        rewritten: list[str] = []
        for index, part in enumerate(parts):
            candidate = replace_sentence(part, f"{seed}:{index}")
            added = sum(1 for a, b in zip(_WORD.findall(part), _WORD.findall(candidate)) if a.lower() != b.lower())
            if total + added > paragraph_cap:
                rewritten.append(part)
            else:
                total += added
                rewritten.append(candidate)
        result.append("".join(rewritten))
    return "".join(result)
