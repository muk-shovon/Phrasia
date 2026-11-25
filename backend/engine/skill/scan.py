"""Single scanner for the local 26-section writing-pattern catalog."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from backend.engine import sentences

DATA = Path(__file__).resolve().parents[1] / "data"
CATALOG_PATH = DATA / "ai_patterns.json"
WORDS_PATH = DATA / "words.json"

_ACRONYMS = {
    "AI", "API", "CEO", "CLI", "CPU", "CSS", "CSV", "CTO", "EU", "GPU",
    "CIA", "FBI", "HTML", "HTTP", "HTTPS", "ID", "IRS", "JSON", "JPG", "ML",
    "NASA", "NATO", "OK", "PDF", "PNG", "RAM", "SaaS", "SQL", "SSD", "UK", "UN",
    "URI", "URL", "USA", "USB", "WHO", "XML",
    "YAML",
}
_EMPHASIS_CAPS = {
    "ALL", "ALWAYS", "BEST", "EVERY", "IMPORTANT", "MUST", "NEVER", "NO", "NONE",
    "NOT", "NOW", "REALLY", "STOP", "WORST",
}
_SECTION_NAMES = {
    1: "Contrasts", 2: "Closers and fragments", 3: "Inflated framing",
    4: "Staged openers", 5: "Unprompted objections", 6: "Triads",
    7: "Repeated openings", 8: "Dashes", 9: "Qualifier stacks",
    10: "Compound hyphens", 11: "Passive or missing subjects",
    12: "Overused formal words", 13: "Inflated significance",
    14: "Vague relationships", 15: "Trailing -ing clauses",
    16: "Sales wording", 17: "Borrowed authority", 18: "Long forms of simple verbs",
    19: "Decorative formatting", 20: "Decorative headings", 21: "Curly quotes",
    22: "Chat residue", 23: "Source-limit disclaimers", 24: "Heading echoes",
    25: "Document narration", 26: "Repeated thread context",
}
_MENTION = re.compile(
    r"(?:\b(?:phrase|word|term|expression|saying)\s*[\"'“‘]?\s*|"
    r"\b(?:called|so-called)\s*)$",
    re.IGNORECASE,
)
_CHAT = re.compile(r"\b(?:lmk|btw|lol|imo|tbh|idk|rn|ngl|omg|wtf)\b", re.IGNORECASE)
_PARAGRAPH = re.compile(r"[^\n]+(?:\n(?![ \t]*\n)[^\n]+)*")
_CONTRAST_SPLIT = re.compile(
    r"\b(?:This|That|It)\s+(?:does|do|is|was)\s+not\s+mean\s+[^.!?]{3,120}\.\s+"
    r"(?:It|This|That)\s+means\s+[^.!?]{3,120}\.",
    re.IGNORECASE,
)
_TRIAD = re.compile(
    r"\b[A-Za-z][\w' -]{0,30},\s+[A-Za-z][\w' -]{0,30},\s+and\s+"
    r"[A-Za-z][\w' -]{0,30}\b",
    re.IGNORECASE,
)
_FORMATTED_TRIAD = re.compile(
    r"\*\*[^*\n]{1,120}\*\*,\s+\*\*[^*\n]{1,120}\*\*,\s+and\s+[^.!?\n]{2,160}",
    re.IGNORECASE,
)
_HEADING = re.compile(r"^(?P<indent>\s*)(?P<marks>#{1,6}\s+)?(?P<body>.*?)\s*$")
_COMMON_HEADING_WORDS = {
    "about", "and", "approach", "background", "benefits", "changes", "check",
    "comparison", "costs", "design", "details", "examples", "for", "from", "how",
    "in", "introduction", "limits", "notes", "of", "options", "overview", "performance",
    "global", "partnerships", "process", "results", "risks", "security", "steps", "summary", "the", "to", "using",
    "what", "when", "why", "with",
}
_HEADING_RELATIONS = {
    "performance": {"fast", "latency", "runtime", "slow", "speed"},
    "security": {"encryption", "risk", "safe", "secure"},
    "cost": {"cost", "price"},
    "pricing": {"cost", "price"},
}
_PRONOUNS = {"he", "i", "it", "she", "they", "we", "you"}
_LOADERS = {
    "a", "an", "her", "his", "its", "my", "our", "that", "the", "their", "there",
    "these", "this", "those",
}


@lru_cache(maxsize=1)
def catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def words() -> list[dict[str, Any]]:
    return json.loads(WORDS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def entries() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in catalog()}


def sections() -> list[int]:
    return sorted({int(item["section"]) for item in catalog()})


def section_name(section: int) -> str:
    return _SECTION_NAMES.get(section, f"Section {section}")


def sentence_case_heading(line: str, document: str) -> str:
    """Lower only common heading words or words seen lowercase in body text."""
    match = _HEADING.match(line)
    if not match:
        return line
    marks = match.group("marks") or ""
    body = match.group("body")
    words_in_heading = body.split()
    body_text = "\n".join(
        part for part in document.splitlines() if not _title_line(part)
    ).lower()
    changed: list[str] = []
    for index, token in enumerate(words_in_heading):
        bare_match = re.search(r"[A-Za-z][A-Za-z'-]*", token)
        if index == 0 or bare_match is None:
            changed.append(token)
            continue
        bare = bare_match.group(0)
        lower = bare.lower()
        if bare.isupper() or not bare[:1].isupper():
            changed.append(token)
            continue
        if lower in _COMMON_HEADING_WORDS or re.search(rf"\b{re.escape(lower)}\b", body_text):
            token = token[:bare_match.start()] + lower + token[bare_match.end():]
        changed.append(token)
    return f"{match.group('indent')}{marks}{' '.join(changed)}"


def _compile(item: dict[str, Any]) -> re.Pattern[str] | None:
    raw = str(item.get("pattern") or "")
    if not raw:
        return None
    pattern = raw if item["kind"] == "regex" else rf"(?<!\w)(?:{raw})(?!\w)"
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


@lru_cache(maxsize=1)
def _compiled() -> tuple[tuple[dict[str, Any], re.Pattern[str]], ...]:
    return tuple(
        (item, compiled)
        for item in catalog()
        if (compiled := _compile(item)) is not None
    )


def _title_line(line: str) -> bool:
    value = line.strip()
    if re.match(r"^#{1,6}\s+", value):
        return True
    if not value or len(value) > 80 or len(value.split()) > 10:
        return False
    if value.endswith((".", "!", "?", ":", ";")):
        return False
    words_in_line = re.findall(r"[A-Za-z][A-Za-z'-]*", value)
    return bool(words_in_line) and sum(word[:1].isupper() for word in words_in_line) >= 1


def _line_spans(text: str, predicate: Any) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if predicate(content):
            spans.append((offset, offset + len(content)))
        offset += len(line)
    return spans


def _context_spans(text: str) -> dict[str, list[tuple[int, int]]]:
    code_patterns = (
        re.compile(r"```[\s\S]*?```"),
        re.compile(r"`[^`\n]*`"),
        re.compile(r"(?:https?|ftp)://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE),
        re.compile(r"(?<!\w)[A-Za-z]:\\(?:[^\s<>:\"|?*]+\\?)+"),
    )
    quote_patterns = (
        re.compile(r'"[^"\n]{1,500}"'),
        re.compile(r"“[^”\n]{1,500}”"),
        re.compile(r"(?<!\w)'[^'\n]{2,300}'(?!\w)"),
        re.compile(r"‘[^’\n]{1,300}’"),
    )
    return {
        "code": [span for pattern in code_patterns for span in _matches(pattern, text)],
        "quotes": [span for pattern in quote_patterns for span in _matches(pattern, text)],
        "titles": _line_spans(text, _title_line),
    }


def _matches(pattern: re.Pattern[str], text: str) -> Iterable[tuple[int, int]]:
    return ((match.start(), match.end()) for match in pattern.finditer(text))


def _overlaps(spans: Iterable[tuple[int, int]], start: int, end: int) -> bool:
    return any(start < right and end > left for left, right in spans)


def _ignored(
    contexts: dict[str, list[tuple[int, int]]],
    names: list[str],
    start: int,
    end: int,
) -> bool:
    return any(_overlaps(contexts.get(name, ()), start, end) for name in names)


def _sentence_start(text: str, position: int) -> bool:
    index = position - 1
    while index >= 0 and text[index] in " \t":
        index -= 1
    return index < 0 or text[index] in ".!?\n\r;:"


def _proper_name(text: str, start: int, value: str) -> bool:
    if not value[:1].isupper():
        return False
    parts = re.findall(r"[A-Za-z]+", value)
    next_word = (
        re.match(r"\s+([A-Z][A-Za-z]+)", text[start + len(value):])
        if value[-1:].isalnum() else None
    )
    if next_word:
        return True
    if _sentence_start(text, start):
        return False
    return bool(parts) and all(part[:1].isupper() for part in parts)


def _mentioned(text: str, position: int) -> bool:
    return bool(_MENTION.search(text[max(0, position - 70):position]))


def _paragraph_index(text: str, position: int) -> int:
    for index, match in enumerate(_PARAGRAPH.finditer(text)):
        if match.start() <= position < match.end():
            return index
    return -1


def _snippet(text: str, start: int, end: int) -> str:
    return " ".join(text[start:end].split())[:140]


def _tell(item: dict[str, Any], text: str, start: int, end: int) -> dict[str, Any]:
    return {
        "section": int(item["section"]),
        "id": str(item["id"]),
        "snippet": _snippet(text, start, end),
        "span": [int(start), int(end)],
        "strength": str(item["strength"]),
        "tier": str(item["tier"]),
        "name": str(item["name"]),
        "action": str(item["action"]),
        "hint": str(item["hint"]),
        "paragraph": _paragraph_index(text, start),
    }


def opening_key(value: str) -> str:
    """Return a conservative key for comparing adjacent sentence openings."""
    found = [word.lower() for word in re.findall(r"[A-Za-z']+", value)[:2]]
    if not found:
        return ""
    if found[0] in _PRONOUNS:
        return found[0]
    if found[0] in _LOADERS:
        return " ".join(found) if len(found) > 1 and found[1] not in _LOADERS else ""
    return found[0]


def _word_allowed(text: str, match: re.Match[str], item: dict[str, Any]) -> bool:
    word = str(item["word"]).lower()
    before = text[max(0, match.start() - 45):match.start()].lower()
    after = text[match.end():match.end() + 45].lower()
    guards = {str(value).lower() for value in item.get("guard", [])}
    nearby = set(re.findall(r"[a-z]+", before[-25:] + " " + after[:25]))
    if guards & nearby:
        return False
    previous = re.findall(r"[a-z]+", before)
    following = re.findall(r"[a-z]+", after)
    prev = previous[-1] if previous else ""
    nxt = following[0] if following else ""
    if word == "highlight" and prev in {"a", "an", "the", "this", "that"}:
        return False
    if word == "key" and nxt in {"and", "are", "is", "to", "was", "were"}:
        return False
    if word == "gate" and prev in {"a", "an", "the"}:
        return False
    if word == "quietly" and nxt not in {
        "becoming", "building", "confident", "growing", "impressive", "one", "powerful", "shaping",
    }:
        return False
    return True


def _mask(text: str, spans: Iterable[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for index in range(start, min(end, len(chars))):
            if chars[index] not in "\r\n":
                chars[index] = " "
    return "".join(chars)


def _sentence_positions(body: str, offset: int) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    cursor = 0
    for piece in sentences.split(body):
        leading = len(piece) - len(piece.lstrip())
        stripped = piece.strip()
        if stripped:
            start = offset + cursor + leading
            result.append((stripped, start, start + len(stripped)))
        cursor += len(piece)
    return result


def _shape_tells(text: str, contexts: dict[str, list[tuple[int, int]]]) -> list[dict[str, Any]]:
    by_id = entries()
    visible = _mask(text, contexts["code"] + contexts["quotes"])
    result: list[dict[str, Any]] = []
    closers: dict[str, list[tuple[int, int]]] = {}

    for paragraph in _PARAGRAPH.finditer(visible):
        body = paragraph.group(0)
        units = _sentence_positions(body, paragraph.start())
        normalized = [unit[0] for unit in units]
        if len(normalized) == 1 and 0 < len(normalized[0].split()) <= 8:
            key = normalized[0].lower().rstrip(".!?")
            closers.setdefault(key, []).append((units[0][1], units[0][2]))

        openings = [opening_key(value) for value in normalized]
        for index in range(max(0, len(openings) - 2)):
            if openings[index] and len(set(openings[index:index + 3])) == 1:
                result.append(_tell(
                    by_id["repeated-openings"], text, units[index][1], units[index + 2][2]
                ))
                break

        run_start: int | None = None
        for index, value in enumerate(normalized + [""]):
            is_fragment = bool(re.match(r"^(?:No|Not)\b", value))
            if is_fragment and run_start is None:
                run_start = index
            if not is_fragment and run_start is not None:
                if index - run_start >= 2:
                    result.append(_tell(
                        by_id["fragment-row"], text, units[run_start][1], units[index - 1][2]
                    ))
                run_start = None

        for index in range(max(0, len(normalized) - 2)):
            window = normalized[index:index + 3]
            starts = [re.findall(r"[A-Za-z']+", value.lower())[:3] for value in window]
            subjects: list[str] = []
            predicates: list[str] = []
            for start_words in starts:
                if start_words and start_words[0] in {"a", "an", "the"}:
                    start_words = start_words[1:]
                subjects.append(start_words[0] if start_words else "")
                predicates.append(start_words[1] if len(start_words) > 1 else "")
            parallel_modal = (
                all(subjects) and all(predicates)
                and len(set(subjects)) == 3 and len(set(predicates)) == 1
            )
            if all(_TRIAD.search(value) for value in window) or parallel_modal:
                result.append(_tell(
                    by_id["triad-paragraph"], text, units[index][1], units[index + 2][2]
                ))
                break

        contrast = _CONTRAST_SPLIT.search(body)
        if contrast:
            result.append(_tell(
                by_id["contrast-split"], text,
                paragraph.start() + contrast.start(), paragraph.start() + contrast.end(),
            ))

    for positions in closers.values():
        if len(positions) > 1:
            for start, end in positions[1:]:
                result.append(_tell(by_id["closer-identical"], text, start, end))

    for match in _FORMATTED_TRIAD.finditer(visible):
        result.append(_tell(by_id["triad-sentence"], text, match.start(), match.end()))

    result.extend(_heading_tells(text, contexts))
    return result


def _normal_heading(value: str) -> str:
    value = re.sub(r"^\s*#{1,6}\s+", "", value)
    value = re.sub(r"[^A-Za-z0-9 ]+", " ", value).lower()
    return " ".join(value.split())


def _heading_tells(text: str, contexts: dict[str, list[tuple[int, int]]]) -> list[dict[str, Any]]:
    by_id = entries()
    result: list[dict[str, Any]] = []
    lines: list[tuple[str, int, int]] = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        lines.append((line, offset, offset + len(line)))
        offset += len(raw)

    lower_body = "\n".join(line for line, _start, _end in lines if not _title_line(line)).lower()
    nonblank = [(index, *entry) for index, entry in enumerate(lines) if entry[0].strip()]
    if len(nonblank) >= 2:
        _first_i, first, _fs, _fe = nonblank[0]
        _second_i, second, second_start, second_end = nonblank[1]
        if _normal_heading(first) and _normal_heading(first) == _normal_heading(second):
            result.append(_tell(by_id["title-echo"], text, second_start, second_end))

    for index, (line, start, end) in enumerate(lines):
        if not _title_line(line) or _overlaps(contexts["code"], start, end):
            continue
        heading = re.sub(r"^\s*#{1,6}\s+", "", line).strip()
        heading_words = re.findall(r"[A-Za-z][A-Za-z'-]*", heading)
        changeable = [
            word for word in heading_words[1:]
            if word[:1].isupper() and not word.isupper()
            and (word.lower() in _COMMON_HEADING_WORDS or re.search(rf"\b{re.escape(word.lower())}\b", lower_body))
        ]
        if changeable:
            result.append(_tell(by_id["heading-titlecase"], text, start, end))

        next_index = index + 1
        while next_index < len(lines) and not lines[next_index][0].strip():
            next_index += 1
        if next_index >= len(lines):
            continue
        candidate, candidate_start, candidate_end = lines[next_index]
        if _title_line(candidate) or len(candidate.split()) > 7:
            continue
        heading_terms = set(re.findall(r"[a-z]+", heading.lower()))
        candidate_terms = set(re.findall(r"[a-z]+", candidate.lower()))
        overlap = len(heading_terms & candidate_terms) / max(len(candidate_terms), 1)
        related = any(
            topic in heading_terms and bool(terms & candidate_terms)
            for topic, terms in _HEADING_RELATIONS.items()
        )
        generic = bool(re.search(r"\b(?:matters|is important|is essential|counts)\b", candidate, re.IGNORECASE))
        if overlap >= 0.6 or (related and generic):
            result.append(_tell(by_id["heading-echo"], text, candidate_start, candidate_end))
    return result


def _gate(tells: list[dict[str, Any]], options: dict[str, Any] | None) -> list[dict[str, Any]]:
    replace_dashes = True if options is None else bool(options.get("replace_dashes", True))
    kept: list[dict[str, Any]] = []
    for tell in tells:
        if tell["strength"] != "weak":
            kept.append(tell)
            continue
        if tell["section"] == 8 and replace_dashes:
            kept.append(tell)
            continue
        paragraph_sections = {
            other["section"] for other in tells
            if other["paragraph"] == tell["paragraph"] and other["section"] != tell["section"]
        }
        if len(paragraph_sections) >= 2 or len(tells) >= 3:
            kept.append(tell)
    return kept


def informal(text: str) -> bool:
    value = (text or "").strip()
    if not value or len(value.split()) > 60:
        return False
    units = sentences.texts(value) or [value]
    if _CHAT.search(value):
        return True
    lower_starts = sum(1 for unit in units if unit[:1].islower())
    if value[:1].islower() and lower_starts * 2 >= len(units) and lower_starts:
        return True
    if len(units) >= 3 and all(len(unit.rstrip(".!?").split()) <= 2 for unit in units):
        return True
    return False


def scan(
    text: str,
    options: dict[str, Any] | None = None,
    *,
    gated: bool = True,
) -> list[dict[str, Any]]:
    """Return gated tells with stable source offsets."""
    source = text or ""
    if not source.strip():
        return []
    contexts = _context_spans(source)
    found: list[dict[str, Any]] = []

    for item, pattern in _compiled():
        skips = list(item["skip_contexts"])
        for match in pattern.finditer(source):
            if match.start() == match.end() or _ignored(contexts, skips, match.start(), match.end()):
                continue
            value = match.group(0)
            if "mentions" in skips and _mentioned(source, match.start()):
                continue
            if item["id"] == "caps-emphasis":
                if value in _ACRONYMS or value not in _EMPHASIS_CAPS:
                    continue
            if item["id"] != "caps-emphasis" and "names" in skips and _proper_name(source, match.start(), value):
                continue
            found.append(_tell(item, source, match.start(), match.end()))

    word_entry = entries()["ai-words"]
    for item in words():
        pattern = re.compile(rf"(?<!\w){re.escape(str(item['word']))}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(source):
            if _ignored(contexts, ["quotes", "code", "titles"], match.start(), match.end()):
                continue
            if _mentioned(source, match.start()) or _proper_name(source, match.start(), match.group(0)):
                continue
            if not _word_allowed(source, match, item):
                continue
            tell = _tell(word_entry, source, match.start(), match.end())
            tell["snippet"] = match.group(0)
            found.append(tell)

    found.extend(_shape_tells(source, contexts))
    found.sort(key=lambda tell: (
        tell["span"][0], tell["tier"] == "C", tell["span"][1], tell["section"], tell["id"]
    ))

    unique: list[dict[str, Any]] = []
    for tell in found:
        duplicate = any(
            previous["id"] == tell["id"] and previous["span"] == tell["span"]
            for previous in unique
        )
        shadowed = any(
            previous["section"] == tell["section"]
            and previous["tier"] != "C" and tell["tier"] == "C"
            and _overlaps([tuple(previous["span"])], tell["span"][0], tell["span"][1])
            for previous in unique
        )
        if not duplicate and not shadowed:
            unique.append(tell)
    return _gate(unique, options) if gated else unique


def survivors(
    text: str,
    found: list[dict[str, Any]],
    options: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all tells in the final text, including any newly introduced ones."""
    found_ids = {str(tell["id"]) for tell in found}
    raw = [tell for tell in scan(text, options, gated=False) if tell["id"] in found_ids]
    introduced = [tell for tell in scan(text, options) if tell["id"] not in found_ids]
    return raw + introduced
