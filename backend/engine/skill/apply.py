"""Deterministic tier-A skill edits and the final per-section report."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Callable

from backend.engine import assemble, blocks, protect, sentences, validators
from backend.engine.lexicon import HEDGES, NEGATIONS
from backend.engine.skill import scan as scanner

_MAX_DROP_WORDS = 18
_ALWAYS_HYPHEN = {
    "cross-functional", "end-to-end", "high-profile", "long-standing", "real-world",
    "self-service", "state-of-the-art", "third-party",
}
_NOT_ONLY_WITH_SUBJECT = re.compile(
    r"\b(?P<subject>(?:It|This|That)\s+(?:is|was)|(?:It's|That's))\s+not\s+"
    r"(?:just|only|merely|simply)\s+(?P<first>[^,;.!?]{1,80}?)\s*,?\s*"
    r"but\s+(?:also\s+)?(?P<second>[^;.!?]{1,100})(?P<stop>[.!?])?$",
    re.IGNORECASE,
)
_NOT_ONLY = re.compile(
    r"\bnot\s+(?:just|only|merely|simply)\s+(?P<first>[^,;.!?]{1,80}?)\s*,?\s*"
    r"but\s+(?:also\s+)?(?P<second>[^;.!?]{1,100})(?P<stop>[.!?])?$",
    re.IGNORECASE,
)
_STAGED_PREFIX = re.compile(
    r"^(?:let's dive in(?:to)?|let's explore|let's break this down|"
    r"here's what you need to know|now let's look at|without further ado|heads up|"
    r"quick note|honestly\?|here's the thing|the thing is|let's be honest|real talk|look,)"
    r"\s*[:,-]?\s*",
    re.IGNORECASE,
)
_DEFENCE_PREFIX = re.compile(r"^(?:to be clear|don't get me wrong)\s*[,;:]\s*", re.IGNORECASE)
_VERDICT_PREFIX = re.compile(r"^(?:overall|ultimately)\s*,\s*", re.IGNORECASE)
_DEEP_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bthe real question is\b", re.I), "the question is"),
    (re.compile(r"\bwhat really matters is\b", re.I), "what matters is"),
    (re.compile(r"\bthe deeper issue is\b", re.I), "the issue is"),
    (re.compile(r"\bthe heart of the matter is\b", re.I), "the issue is"),
    (re.compile(r"^(?:at its core|fundamentally|in reality|in essence),?\s*", re.I), ""),
)
_QUALIFIERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcould potentially(?: possibly)?\b", re.I), "could"),
    (re.compile(r"\bmight arguably\b", re.I), "might"),
    (re.compile(r"\bmay possibly\b", re.I), "may"),
    (re.compile(r"\b(possibly) be argued\b", re.I), "be argued"),
    (re.compile(r"\bin some cases it may\b", re.I), "it may"),
    (re.compile(r"\bit is possible that\s*", re.I), "possibly "),
    (re.compile(r"\bit's also possible that\s*", re.I), "possibly "),
)
_HYPHEN = re.compile(
    r"\b(is|are|was|were|seems|seem|looks|look|feels|feel|becomes|become)\s+"
    r"([a-z]+)-([a-z]+)\b",
    re.IGNORECASE,
)
_SIGNIFICANCE_TAIL = re.compile(
    r",\s*(?:marking|shaping|cementing|solidifying|establishing|representing)\b"
    r"[^.;!?]{0,110}[.!?]?\s*$",
    re.IGNORECASE,
)
_ING_TAIL = re.compile(
    r",\s*(?:highlighting|underscoring|emphasizing|reflecting|symbolizing|"
    r"contributing to|cultivating|fostering|encompassing|showcasing|ensuring)\b"
    r"[^.;!?]{0,120}[.!?]?\s*$",
    re.IGNORECASE,
)
_STOCK_CLOSER = re.compile(
    r"\b(?:that is the real win|that distinction matters|read that again|let that sink in|"
    r"that is the whole point|the future looks bright|exciting times (?:lie )?ahead|"
    r"a step in the right direction)\b",
    re.IGNORECASE,
)
_CHAT_WHOLE = re.compile(
    r"^(?:great question|of course|certainly|you're absolutely right|i hope this helps|"
    r"let me know if\b.*|would you like\b.*|want me to\b.*|should i continue\b.*)[.!?]*$",
    re.IGNORECASE,
)
_OVERVIEW = re.compile(
    r"^here(?: is|'s) (?:an overview|a summary) of (?P<topic>.+?)[.!?]$",
    re.IGNORECASE,
)
_DASH_PAIR = re.compile(
    r"\s+(?:--|[\u2014\u2013])\s+(?P<aside>[^\u2014\u2013;]{1,120}?)\s+"
    r"(?:--|[\u2014\u2013])\s+"
)
_DASH_TOKEN = re.compile(r"\s*(?:[\u2014\u2013]|(?<=\s)--(?=\s))\s*")
_NUMERIC_RANGE = re.compile(r"(?<=\d)\s*[\u2014\u2013]\s*(?=\d)")
_COPULA = re.compile(
    r"\b(serves|stands|functions|operates|served|stood|functioned|operated)\s+as\b",
    re.IGNORECASE,
)
_HAS = re.compile(
    r"\b(boasts|features|offers|maintains)\s+"
    r"(?=(?:a|an|over|\d|one|two|three|four|five|six|seven|eight|nine|ten|many|several)\b)",
    re.IGNORECASE,
)
_SALES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bnestled (?:within|in)\b", re.I), "in"),
    (re.compile(r"\bin the heart of\b", re.I), "in"),
    (re.compile(r"\brich cultural heritage\b", re.I), "cultural history"),
    (re.compile(r"\bnatural beauty\b", re.I), "scenery"),
    (re.compile(r"\bdiverse array(?: of)?\b", re.I), "range of"),
    (re.compile(r"\bcommitment to\b", re.I), "support for"),
    (re.compile(r"\bbreathtaking\b", re.I), "striking"),
    (re.compile(r"\bstunning\b", re.I), "striking"),
    (re.compile(r"\brenowned\b", re.I), "well-known"),
    (re.compile(r"\bgroundbreaking\b", re.I), "new"),
    (re.compile(r"\bprofound\b", re.I), "deep"),
    (re.compile(r"\bvibrant\b", re.I), "lively"),
    (re.compile(r"\bmust-visit\b", re.I), "popular with visitors"),
    (re.compile(r"\bexemplifies\b", re.I), "shows"),
    (re.compile(r"\bfeaturing\b", re.I), "with"),
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _capitalise(text: str) -> str:
    stripped = text.lstrip()
    return stripped[:1].upper() + stripped[1:] if stripped else stripped


def droppable(span: str, *, sentence: bool = False) -> bool:
    """Return whether a rule may remove this exact span."""
    value = (span or "").strip()
    if not value or _word_count(value) > _MAX_DROP_WORDS:
        return False
    if re.search(r"\d|(?:https?://|www\.|\b[\w.+-]+@[\w.-]+\.)", value, re.I):
        return False
    if re.search(r"[\"“”`]|\[PHRASIA_PROTECT_", value):
        return False
    lowered = {word.lower() for word in re.findall(r"[A-Za-z']+", value)}
    if lowered & (HEDGES | NEGATIONS) or re.search(r"\b(?:don't|doesn't|didn't|isn't|aren't|wasn't|weren't)\b", value, re.I):
        return False
    parts = value.split(None, 1)
    name_probe = parts[1] if sentence and len(parts) > 1 else ("" if sentence else value)
    return re.search(r"\b[A-Z][a-z]{2,}\b", name_probe) is None


def _new_tell(original: str, candidate: str, options: dict[str, Any]) -> bool:
    before = Counter(tell["id"] for tell in scanner.scan(original, options))
    after = Counter(tell["id"] for tell in scanner.scan(candidate, options))
    return any(count > before.get(tell_id, 0) for tell_id, count in after.items())


def _accept(
    original: str,
    candidate: str,
    options: dict[str, Any],
    *,
    dropped: str = "",
    formula: bool = False,
) -> str:
    candidate = candidate.strip()
    if not candidate or candidate == original.strip():
        return original
    at_start = original.lstrip().startswith(dropped.strip()) if dropped else False
    if dropped and not droppable(dropped, sentence=at_start):
        return original
    validation_source = original
    if formula:
        validation_source = re.sub(r"\bnot\s+(?:just|only|merely|simply)\s+", "", original, flags=re.I)
        validation_source = re.sub(r",?\s+but\s+(?:also\s+)?", " and ", validation_source, flags=re.I)
    ok, _reasons = validators.validate(
        validation_source,
        candidate,
        dropped_by_rule=[dropped] if dropped else (),
    )
    if not ok and dropped:
        ratio = _word_count(candidate) / max(_word_count(original), 1)
        ok = (
            validators.preserve_critical(original, candidate)
            and validators.grammar_sanity(candidate)
            and 0.3 <= ratio <= 1.2
        )
    if not ok and formula:
        ratio = _word_count(candidate) / max(_word_count(validation_source), 1)
        ok = (
            validators.preserve_critical(validation_source, candidate)
            and validators.content_retention(validation_source, candidate) >= 0.9
            and validators.grammar_sanity(candidate)
            and 0.7 <= ratio <= 1.2
        )
    if not ok or _new_tell(original, candidate, options):
        return original
    return candidate


def _log(dropped: list[dict[str, Any]], section: int, rule_id: str, snippet: str) -> None:
    value = " ".join(snippet.split())
    if not value:
        return
    dropped.append({"section": section, "id": rule_id, "snippet": value})


def _case_like(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _span_pass(
    source: str,
    found: list[dict[str, Any]],
    options: dict[str, Any],
    dropped: list[dict[str, Any]],
) -> str:
    word_map = {str(item["word"]).lower(): str(item["replacement"]) for item in scanner.words()}
    operations: list[tuple[int, int, str, int, str, bool]] = []
    straight_quotes = bool(options.get("straight_quotes", True))
    quote_map = {"“": '"', "”": '"', "‘": "'", "’": "'"}

    for tell in found:
        start, end = map(int, tell["span"])
        snippet = source[start:end]
        replacement: str | None = None
        is_drop = False
        priority = 2
        if tell["id"] == "ai-words":
            replacement = word_map.get(snippet.lower())
            if replacement:
                replacement = _case_like(snippet, replacement)
        elif tell["id"] == "curly-quotes" and straight_quotes:
            replacement = quote_map.get(snippet)
        elif tell["id"] == "caps-emphasis":
            replacement = snippet.lower()
            if start == 0 or source[max(0, start - 2):start].rstrip().endswith(tuple(".!?")):
                replacement = _capitalise(replacement)
        elif tell["id"] == "dotted-emphasis":
            replacement = re.sub(r"\.\s+", " ", snippet[:-1]) + "."
        elif tell["id"] in {"heading-echo", "title-echo"}:
            if tell["id"] == "title-echo" or droppable(snippet, sentence=True):
                replacement = ""
                is_drop = True
                priority = 0
        if replacement is not None and replacement != snippet:
            operations.append((start, end, replacement, priority, tell["id"], is_drop))

    selected: list[tuple[int, int, str, int, str, bool]] = []
    for operation in sorted(operations, key=lambda row: (row[3], row[0], -(row[1] - row[0]))):
        if any(operation[0] < old[1] and operation[1] > old[0] for old in selected):
            continue
        selected.append(operation)

    result = source
    by_id = scanner.entries()
    for start, end, replacement, _priority, rule_id, is_drop in sorted(selected, reverse=True):
        snippet = result[start:end]
        result = result[:start] + replacement + result[end:]
        if is_drop:
            _log(dropped, int(by_id[rule_id]["section"]), rule_id, snippet)
    return result


def _line_pass(
    text: str,
    active_ids: set[str],
    dropped: list[dict[str, Any]],
) -> str:
    out: list[str] = []
    for raw in text.splitlines(keepends=True):
        ending = raw[len(raw.rstrip("\r\n")):]
        line = raw[:-len(ending)] if ending else raw
        if "horizontal-rule" in active_ids and re.fullmatch(r"[ \t]*---[ \t]*", line):
            _log(dropped, 20, "horizontal-rule", line)
            continue
        if "bold-decoration" in active_ids:
            def plain_bold(match: re.Match[str]) -> str:
                value = match.group(1)
                acronym_first = re.match(r"^([A-Z]{2,}s?)\s+\([^)]{3,100}\)$", value)
                acronym_last = re.match(r"^(.+?)\s+\([A-Z]{2,}\)$", value)
                if acronym_first:
                    return acronym_first.group(1)
                if acronym_last:
                    return acronym_last.group(1)
                return value

            line = re.sub(r"\*\*([^*\n]{1,160})\*\*", plain_bold, line)
            line = re.sub(r"\bsuch as the\b", "like the", line, flags=re.IGNORECASE)
        if "emoji-decoration" in active_ids:
            line = re.sub(
                r"^[ \t>#*-]*(?:[\U0001F300-\U0001FAFF\u2190-\u21FF\u2600-\u27BF]+\s*)+",
                "",
                line,
            )
        if "heading-titlecase" in active_ids:
            line = scanner.sentence_case_heading(line, text)
        out.append(line + ending)
    return "".join(out)


def _not_only(value: str, options: dict[str, Any]) -> str:
    match = _NOT_ONLY_WITH_SUBJECT.search(value)
    if match:
        candidate = (
            value[:match.start()] + f"{match.group('subject')} {match.group('first')} and "
            f"{match.group('second')}{match.group('stop') or ''}"
        )
        return _accept(value, candidate, options, formula=True)
    match = _NOT_ONLY.search(value)
    if not match:
        return value
    candidate = (
        value[:match.start()] + f"{match.group('first')} and {match.group('second')}"
        f"{match.group('stop') or ''}"
    )
    return _accept(value, candidate, options, formula=True)


def _dashes(value: str) -> str:
    result = _NUMERIC_RANGE.sub("-", value)
    result = _DASH_PAIR.sub(lambda match: f", {match.group('aside').strip()}, ", result)
    while True:
        match = _DASH_TOKEN.search(result)
        if not match:
            break
        left = result[:match.start()].rstrip()
        right = result[match.end():].lstrip()
        if not right:
            replacement = ""
        elif re.match(r"^(?:for example|namely|including|such as|the following)\b", right, re.I):
            replacement = ": "
        elif re.match(r"^(?:I|We|You|He|She|They|It|This|That|The)\b", right) and re.search(
            r"\b(?:am|are|can|could|did|do|does|has|have|is|may|might|must|should|was|were|will|would)\b",
            right,
            re.I,
        ):
            replacement = ". "
        elif re.search(r"\b(?:includes?|contains?|offers?|has|are|is)\b[^.!?]*$", left, re.I):
            replacement = ": "
        else:
            replacement = ", "
        result = left + replacement + right
    return result


def _hyphens(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        compound = f"{match.group(2)}-{match.group(3)}"
        return match.group(0) if compound.lower() in _ALWAYS_HYPHEN else f"{match.group(1)} {compound.replace('-', ' ')}"
    return _HYPHEN.sub(replace, value)


def _copulas(value: str) -> str:
    forms = {
        "serves": "is", "stands": "is", "functions": "is", "operates": "is",
        "served": "was", "stood": "was", "functioned": "was", "operated": "was",
    }
    value = _COPULA.sub(lambda match: _case_like(match.group(1), forms[match.group(1).lower()]), value)
    value = re.sub(r"\bboasts\s+over\s+", "has more than ", value, flags=re.IGNORECASE)
    value = _HAS.sub(lambda match: _case_like(match.group(1), "has") + " ", value)
    value = re.sub(r"\bhas\s+(.+?)\s+and\s+has\s+more than\b", r"has \1 and more than", value, flags=re.IGNORECASE)
    return re.sub(r"\brepresents\s+(?=(?:a|an)\b)", "is ", value, flags=re.I)


def _sales(value: str) -> str:
    for pattern, replacement in _SALES:
        value = pattern.sub(replacement, value)
    return re.sub(r"[ \t]{2,}", " ", value)


def _whole_drop(value: str, active_ids: set[str]) -> tuple[bool, int, str]:
    stripped = value.strip()
    if _word_count(stripped) > _MAX_DROP_WORDS or not droppable(stripped, sentence=True):
        return False, 0, ""
    if "closer-stock" in active_ids and _STOCK_CLOSER.search(stripped):
        return True, 2, "closer-stock"
    if "stock-closing" in active_ids and _STOCK_CLOSER.search(stripped):
        return True, 13, "stock-closing"
    if "chatbot-residue" in active_ids and _CHAT_WHOLE.fullmatch(stripped):
        return True, 22, "chatbot-residue"
    if "staged-opener" in active_ids and _STAGED_PREFIX.fullmatch(stripped):
        return True, 4, "staged-opener"
    return False, 0, ""


def _edit_sentence(
    core: str,
    active_ids: set[str],
    options: dict[str, Any],
    dropped: list[dict[str, Any]],
) -> str:
    value = core.strip()
    if "contrast-not-only" in active_ids:
        value = _not_only(value, options)

    prefix_rules = (
        ("closer-overall", 2, _VERDICT_PREFIX),
        ("staged-opener", 4, _STAGED_PREFIX),
        ("arguing-marker", 5, _DEFENCE_PREFIX),
    )
    for rule_id, section, pattern in prefix_rules:
        if rule_id not in active_ids:
            continue
        match = pattern.match(value)
        if not match:
            continue
        removed = match.group(0)
        candidate = _capitalise(value[match.end():])
        accepted = _accept(value, candidate, options, dropped=removed)
        if accepted != value:
            value = accepted
            _log(dropped, section, rule_id, removed)

    if "deep-light" in active_ids or "deep-drop" in active_ids:
        for pattern, replacement in _DEEP_REPLACEMENTS:
            candidate = pattern.sub(replacement, value, count=1)
            if candidate != value:
                removed = value[: len(value) - len(candidate)] if replacement == "" else ""
                accepted = _accept(value, _capitalise(candidate), options, dropped=removed)
                if accepted != value:
                    value = accepted

    transforms: tuple[tuple[str, Callable[[str], str]], ...] = (
        ("dashes", _dashes),
        ("qualifier-stack", lambda text: _apply_table(text, _QUALIFIERS)),
        ("hyphen-after-verb", _hyphens),
        ("sales-words", _sales),
        ("copula-as", _copulas),
        ("boasts-features", _copulas),
    )
    for rule_id, transform in transforms:
        if rule_id not in active_ids:
            continue
        candidate = transform(value)
        if candidate != value:
            value = _accept(value, candidate, options, formula=rule_id == "qualifier-stack")

    for rule_id, section, pattern in (
        ("significance-tail", 13, _SIGNIFICANCE_TAIL),
        ("shallow-ing", 15, _ING_TAIL),
    ):
        if rule_id not in active_ids:
            continue
        match = pattern.search(value)
        if not match or not droppable(match.group(0)):
            continue
        candidate = value[:match.start()].rstrip()
        if not candidate.endswith((".", "!", "?")):
            candidate += "."
        accepted = _accept(value, candidate, options, dropped=match.group(0))
        if accepted != value:
            _log(dropped, section, rule_id, match.group(0))
            value = accepted
    return value


def _apply_table(value: str, table: tuple[tuple[re.Pattern[str], str], ...]) -> str:
    for pattern, replacement in table:
        value = pattern.sub(replacement, value)
    return re.sub(r"[ \t]{2,}", " ", value)


def _merge_overviews(
    items: list[str],
    options: dict[str, Any],
    dropped: list[dict[str, Any]],
) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(items):
        match = _OVERVIEW.fullmatch(items[index].strip())
        if match and index + 1 < len(items):
            following = items[index + 1].strip()
            follow_match = re.match(r"^(?:It|This|They)\s+(.+)$", following, re.I)
            if follow_match:
                topic = match.group("topic").strip()
                candidate = f"{_capitalise(topic)} {follow_match.group(1)}"
                source = f"{items[index].strip()} {following}"
                wrapper = items[index][:match.start("topic")]
                accepted = _accept(source, candidate, options, dropped=wrapper)
                if accepted != source:
                    result.append(accepted)
                    _log(dropped, 22, "chatbot-residue", wrapper)
                    index += 2
                    continue
        result.append(items[index])
        index += 1
    return result


def _merge_fragments(items: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(items):
        if re.match(r"^No\b", items[index]) and index + 1 < len(items) and re.match(r"^No\b", items[index + 1]):
            first = re.sub(r"^No\s+", "", items[index], flags=re.I).rstrip(". ")
            second = re.sub(r"^No\s+", "", items[index + 1], flags=re.I).rstrip(". ")
            candidate = f"No {first} or {second[:1].lower()}{second[1:]}."
            if validators.grammar_sanity(candidate):
                result.append(candidate)
                index += 2
                continue
        result.append(items[index])
        index += 1
    return result


def _edit_block(
    text: str,
    active_ids: set[str],
    options: dict[str, Any],
    dropped: list[dict[str, Any]],
) -> str:
    items = sentences.texts(text)
    if not items:
        return text
    if "chatbot-residue" in active_ids:
        items = _merge_overviews(items, options, dropped)
    edited: list[str] = []
    for item in items:
        should_drop, section, rule_id = _whole_drop(item, active_ids)
        if should_drop:
            _log(dropped, section, rule_id, item)
            continue
        edited.append(_edit_sentence(item, active_ids, options, dropped))
    if "fragment-row" in active_ids:
        edited = _merge_fragments(edited)
    for index in range(1, len(edited)):
        current = re.match(r"^The\s+([A-Za-z]+)\s+has\b", edited[index])
        previous = re.match(r"^([A-Za-z]+)\b", edited[index - 1])
        if current and previous and current.group(1).lower() == previous.group(1).lower():
            edited[index] = re.sub(r"^The\s+[A-Za-z]+", "It", edited[index], count=1)
    return " ".join(item for item in edited if item.strip())


def _block_pass(
    text: str,
    active_ids: set[str],
    options: dict[str, Any],
    dropped: list[dict[str, Any]],
) -> str:
    parsed = blocks.parse(text)
    replacements: list[str] = []
    for block in parsed:
        if block.kind in {"heading", "empty"}:
            replacements.append(block.text)
            continue
        staged_label = "staged-opener" in active_ids and _STAGED_PREFIX.match(block.text)
        working = block.body if block.label and block.body and not staged_label else block.text
        edited = _edit_block(working, active_ids, options, dropped)
        if block.label and block.body and not staged_label:
            replacements.append(block.text.replace(block.body, edited, 1))
        else:
            replacements.append(edited)
    return assemble.assemble(parsed, replacements)


def _repeated_closer_pass(
    text: str,
    found: list[dict[str, Any]],
    dropped: list[dict[str, Any]],
) -> str:
    keys = {
        " ".join(tell["snippet"].split()).lower().rstrip(".!?")
        for tell in found if tell["id"] == "closer-identical"
    }
    if not keys:
        return text
    seen: set[str] = set()
    out: list[str] = []
    for raw in text.splitlines(keepends=True):
        value = " ".join(raw.split()).lower().rstrip(".!?")
        if value in keys and value in seen and droppable(raw, sentence=True):
            _log(dropped, 2, "closer-identical", raw)
            continue
        if value:
            seen.add(value)
        out.append(raw)
    return "".join(out)


def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)
    text = re.sub(r"[ \t]+\r?\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _informal_hold(
    source: str,
    tells: list[dict[str, Any]],
    options: dict[str, Any],
) -> bool:
    if not scanner.informal(source) or any(tell["section"] == 22 for tell in tells):
        return False
    if bool(options.get("replace_dashes", True)) and any(tell["section"] == 8 for tell in tells):
        return False
    return len({tell["section"] for tell in tells}) <= 1


def build_report(
    source: str,
    final: str,
    found: list[dict[str, Any]],
    remaining: list[dict[str, Any]],
    *,
    dropped_by_rule: list[dict[str, Any]] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    del source, final
    found_counts = Counter(int(tell["section"]) for tell in found)
    final_counts = Counter(int(tell["section"]) for tell in remaining)
    section_ids = sorted(set(found_counts) | set(final_counts))
    sections_out: list[dict[str, Any]] = []
    for section in section_ids:
        found_count = found_counts[section]
        survived = min(found_count, final_counts[section]) if found_count else final_counts[section]
        sections_out.append({
            "section": section,
            "name": scanner.section_name(section),
            "found": found_count,
            "fixed": max(0, found_count - survived),
            "survived": survived,
            "review": final_counts[section],
        })

    review: list[dict[str, Any]] = []
    seen: set[tuple[int, str, int, int]] = set()
    for tell in remaining:
        start, end = map(int, tell["span"])
        key = (int(tell["section"]), str(tell["id"]), start, end)
        if key in seen:
            continue
        seen.add(key)
        review.append({
            "section": int(tell["section"]),
            "name": str(tell["name"]),
            "snippet": str(tell["snippet"]),
            "hint": str(tell["hint"]),
            "span": [start, end],
            "tier": str(tell["tier"]),
        })
    survived_total = sum(row["survived"] for row in sections_out if row["found"])
    return {
        "found": len(found),
        "fixed": max(0, len(found) - survived_total),
        "survived": survived_total,
        "sections": sections_out,
        "review": review,
        "dropped_by_rule": dropped_by_rule or [],
        "reason": reason,
    }


def apply_skill(
    text: str,
    options: dict[str, Any] | None = None,
    *,
    found: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Apply gated tier-A edits and return the edited text plus its report."""
    source = text or ""
    settings = {"replace_dashes": True, "straight_quotes": True, **(options or {})}
    active = scanner.scan(source, settings)
    original_tells = active if found is None else found
    if _informal_hold(source, active, settings):
        return source, build_report(
            source, source, original_tells, original_tells, reason="informal register"
        )

    dropped: list[dict[str, Any]] = []
    active_ids = {
        str(tell["id"]) for tell in active
        if tell["tier"] == "A" and tell["action"] != "flag"
        and not (tell["id"] == "dashes" and not bool(settings["replace_dashes"]))
    }
    working = _span_pass(source, active, settings, dropped)
    masked, protected = protect.extract(working)
    masked = _line_pass(masked, active_ids, dropped)
    masked = _block_pass(masked, active_ids, settings, dropped)
    masked = _tidy(masked)
    restored = protect.restore(masked, protected)
    if restored is None:
        restored = working
    restored = _repeated_closer_pass(restored, active, dropped)
    remaining = scanner.survivors(restored, original_tells, settings)
    return restored, build_report(
        source,
        restored,
        original_tells,
        remaining,
        dropped_by_rule=dropped,
    )
