"""Sentence-by-sentence hosted rewriting.

One provider call rewrites one sentence, or one adjacent pair when the planner
chooses ``merge``. The whole document is never sent in a single call. Each
sentence is segmented, analysed, planned, rewritten, validated, meaning-checked,
and then the finished text is rescanned so only flagged sentences are retried.
"""
from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from backend.engine import assemble, blocks, protect, sentences, validators
from backend.engine.llm import meaning
from backend.engine.llm.chain import LLMChain
from backend.engine.llm.prompts import avoid_phrase, build_sentence_rewrite, load_prompt
from backend.engine.llm.sentence_ops import (
    SentenceInfo, analyze, instruction, label, plan,
)
from backend.engine.skill import scan as skill_scan

Progress = Callable[[str, int, int, str], None]
_MAX_ROUNDS = {"light": 1, "medium": 2, "heavy": 3, "ninja": 4}
_DEFAULT_WORKERS = 4
_WRAPPER = re.compile(
    r"^\s*(?:here(?:'s| is)|below is|sure[,!]?|certainly[,!]?|the rewritten sentence(?:s)? is)\b[^\n]{0,120}:\s*",
    re.IGNORECASE,
)
_NUMBERED = re.compile(r"^\s*\d+[.)]\s*", re.MULTILINE)

_BOUNDS = {
    "synonym": (0.75, 1.35, 0.55),
    "clause": (0.75, 1.4, 0.52),
    "opening": (0.75, 1.4, 0.52),
    "punchy": (0.45, 1.25, 0.5),
    "split": (0.8, 2.2, 0.5),
    "merge": (0.45, 1.65, 0.5),
    "keep": (0.8, 1.2, 0.55),
}


def _emit(callback: Progress | None, stage: str, current: int, total: int, message: str) -> None:
    if callback is None:
        return
    try:
        callback(stage, current, total, message)
    except Exception:
        pass


def density(text: str, options: dict[str, Any] | None = None) -> float:
    """Pattern sightings per 100 words in the current text."""
    words = len((text or "").split())
    if not words:
        return 0.0
    count = len(skill_scan.scan(text, options, gated=False))
    return round(count * 100 / words, 2)


def passes_for(intensity: str) -> int:
    return _MAX_ROUNDS.get((intensity or "").strip().lower(), 1)


def _strip_wrapper(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^<sentence>\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*</sentence>$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^<passage>\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*</passage>$", "", value, flags=re.IGNORECASE)
    if value.startswith("```") and value.endswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", value)
        value = re.sub(r"\n?```\s*$", "", value)
    value = _WRAPPER.sub("", value)
    value = _NUMBERED.sub("", value).strip()
    if len(value) >= 2 and value[0] in "\"'“”" and value[-1] in "\"'“”":
        value = value[1:-1].strip()
    return value


def _restore(masked: str, spans: list[protect.Span]) -> str | None:
    exact = protect.restore(masked, spans)
    if exact is not None:
        return exact
    result = masked
    for span in spans:
        number = re.sub(r"\D", "", span.placeholder)
        pattern = re.compile(
            rf"\[?\s*PHRASIA[\s_-]*PROTECT[\s_-]*{number}\s*\]?",
            re.IGNORECASE,
        )
        if len(pattern.findall(result)) != 1:
            return None
        result = pattern.sub(lambda _match, value=span.original: value, result, count=1)
    if re.search(r"PHRASIA[\s_-]*PROTECT", result, re.IGNORECASE):
        return None
    return result


def _tidy(text: str) -> str:
    value = re.sub(r"[ \t]{2,}", " ", text or "")
    value = re.sub(r"[ \t]+([,.;:!?])", r"\1", value)
    return value.strip()


# ---------------------------------------------------------------------------
# Compatibility path used by direct chunk tests and the sentence endpoint
# ---------------------------------------------------------------------------

def _chunk_prompt(
    text: str, *, tone: str, strength: str, avoid: str, strict: bool
) -> tuple[str, str]:
    system = load_prompt("rewrite_system.md")
    system = system.replace("{tone}", tone).replace("{strength}", strength)
    system = system.replace("{avoid}", avoid)
    if strict:
        system += (
            "\n\nThe previous draft changed a protected detail or drifted in length. "
            "Write it again and keep every number, name, URL, citation, hedge and "
            "negation exactly."
        )
    user = f"<passage>\n{text}\n</passage>"
    return system, user


def rewrite_chunk(
    chain: LLMChain,
    core: str,
    *,
    tone: str,
    strength: str,
    avoid: str,
    examples: Iterable[dict[str, Any]] = (),
    polish: bool = False,
    burstiness: bool = False,
) -> tuple[str, bool, list[str]]:
    """Rewrite one protected chunk. Kept for sentence refresh and tests."""
    masked, spans = protect.extract(core)
    if not masked.strip():
        return core, False, ["empty"]
    reasons: list[str] = []
    for strict in (False, True):
        system, user = _chunk_prompt(
            masked, tone=tone, strength=strength, avoid=avoid, strict=strict
        )
        completion = chain.complete(system, user)
        restored = _restore(_strip_wrapper(completion.text), spans)
        if restored is None:
            reasons.append("placeholder")
            continue
        restored = _tidy(restored)
        ok, failures = validators.validate(
            core, restored, content_min=0.55, length_min=0.6, length_max=1.6
        )
        if ok and restored:
            return restored, True, []
        reasons.extend(failures)
    return core, False, reasons


# ---------------------------------------------------------------------------
# Document segmentation and the per-sentence plan
# ---------------------------------------------------------------------------

@dataclass
class _Slot:
    block_index: int
    piece_index: int
    core: str
    trailing: str


@dataclass
class _Unit:
    start: int
    end: int
    operation: str
    source: str
    text: str
    validator: str = "passed"
    meaning_score: float = 0.0
    reason: str = ""
    attempts: int = 1
    flags: list[str] = field(default_factory=list)


def _segments(text: str) -> tuple[list[blocks.Block], list[_Slot]]:
    parsed = blocks.parse(text)
    slots: list[_Slot] = []
    for block_index, block in enumerate(parsed):
        working = block.body if block.label and block.body else block.text
        if block.kind in {"heading", "empty"} or not working.strip():
            continue
        for piece_index, piece in enumerate(sentences.split(working)):
            core = piece.rstrip()
            trailing = piece[len(core):]
            if core.strip():
                slots.append(
                    _Slot(
                        block_index=block_index,
                        piece_index=piece_index,
                        core=core.strip(),
                        trailing=trailing,
                    )
                )
    return parsed, slots


def _assemble(parsed: list[blocks.Block], slots: list[_Slot], units: list[_Unit]) -> str:
    outputs: dict[int, str] = {
        index: f"{slot.core}{slot.trailing}" for index, slot in enumerate(slots)
    }
    for unit in units:
        outputs[unit.start] = f"{unit.text}{slots[unit.end].trailing}"
        for index in range(unit.start + 1, unit.end + 1):
            outputs[index] = ""
    by_block: dict[int, list[str]] = {}
    for index, slot in enumerate(slots):
        by_block.setdefault(slot.block_index, []).append(outputs[index])
    replacements: list[str] = []
    for block_index, block in enumerate(parsed):
        new_body = "".join(by_block.get(block_index, []))
        if block_index not in by_block:
            replacements.append(block.text)
        elif block.label and block.body:
            replacements.append(block.text.replace(block.body, new_body, 1))
        else:
            replacements.append(new_body)
    return assemble.assemble(parsed, replacements)


def _context(slots: list[_Slot], unit: _Unit) -> tuple[str, str]:
    previous = slots[unit.start - 1].core if unit.start > 0 else ""
    following = slots[unit.end + 1].core if unit.end + 1 < len(slots) else ""
    return previous, following


def _sentence_count(value: str) -> int:
    return len(sentences.texts(value))


def _meaning_ok(
    chain: LLMChain,
    source: str,
    candidate: str,
    *,
    use_llm: bool,
) -> tuple[bool, float, str]:
    return meaning.assess(chain, source, candidate, use_llm=use_llm)


def _rewrite_unit(
    chain: LLMChain,
    unit: _Unit,
    slots: list[_Slot],
    *,
    tone: str,
    strength: str,
    options: dict[str, Any],
    use_llm_meaning: bool = True,
) -> _Unit:
    """Rewrite one unit; keep the source when both attempts fail validation."""
    source = unit.source
    masked, spans = protect.extract(source)
    previous, following = _context(slots, unit)
    examples = _examples_for(tone, strength, source, unit.operation)
    avoid = avoid_phrase(skill_scan.scan(source, options)) if source else "none"
    length_min, length_max, content_min = _BOUNDS.get(
        unit.operation, _BOUNDS["synonym"]
    )
    reasons: list[str] = []

    for strict in (False, True):
        system, user = build_sentence_rewrite(
            masked,
            operation=unit.operation,
            instruction=instruction(unit.operation),
            tone=tone,
            strength=strength,
            avoid=avoid,
            previous=previous,
            following=following,
            examples=examples,
            strict=strict,
        )
        try:
            completion = chain.complete(
                system, user, max_tokens=max(256, min(900, len(source.split()) * 4))
            )
        except Exception as exc:  # provider failure is handled by the caller
            raise exc
        candidate = _restore(_strip_wrapper(completion.text), spans)
        if candidate is None:
            reasons.append("placeholder")
            continue
        candidate = _tidy(candidate)
        if not candidate:
            reasons.append("empty")
            continue

        count = _sentence_count(candidate)
        if unit.operation == "merge" and count != 1:
            reasons.append("sentence_count")
            continue
        if unit.operation == "split" and count != 2:
            reasons.append("sentence_count")
            continue
        if unit.operation not in {"merge", "split"} and count > 1:
            reasons.append("sentence_count")
            continue

        ok, failures = validators.validate(
            source,
            candidate,
            length_min=length_min,
            length_max=length_max,
            content_min=content_min,
        )
        if not ok:
            reasons.extend(failures)
            continue

        meaning_ok, score, meaning_reason = _meaning_ok(
            chain, source, candidate, use_llm=use_llm_meaning
        )
        if not meaning_ok:
            reasons.append(meaning_reason)
            continue

        accepted = _Unit(
            start=unit.start,
            end=unit.end,
            operation=unit.operation,
            source=source,
            text=candidate,
            validator="passed",
            meaning_score=score,
            attempts=1 if not strict else 2,
        )
        return accepted

    return _Unit(
        start=unit.start,
        end=unit.end,
        operation="keep",
        source=source,
        text=source,
        validator="kept:" + ",".join(dict.fromkeys(reasons)) if reasons else "kept",
        meaning_score=meaning.similarity(source, source),
        attempts=2,
    )


def _examples_for(
    tone: str, strength: str, source: str, operation: str
) -> list[dict[str, Any]]:
    try:
        from backend.engine.llm import retrieval

        return retrieval.retrieve(
            tone, strength, source, limit=3, operation=operation
        )
    except Exception:
        return []


def _unit_flags(unit: _Unit, options: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    tells = skill_scan.scan(unit.text, options, gated=False)
    for tell in tells[:3]:
        flags.append(f"pattern:{tell.get('id', 'unknown')}")
    if unit.operation == "keep" and tells:
        flags.append("kept_with_signal")
    if unit.text != unit.source:
        gap = meaning.similarity(unit.source, unit.text)
        if gap > 0.92 and skill_scan.scan(unit.source, options, gated=False):
            flags.append("low-change")
    return flags[:4]


def _rehumanize_operation(unit: _Unit, options: dict[str, Any]) -> str:
    length = len(unit.text.split())
    if skill_scan.scan(unit.text, options, gated=False) and length > 20:
        return "punchy"
    if length > 26:
        return "split"
    return "synonym"


def _workers() -> int:
    try:
        value = int(os.environ.get("PHRASIA_LLM_CONCURRENCY", str(_DEFAULT_WORKERS)))
    except ValueError:
        return _DEFAULT_WORKERS
    return max(1, min(8, value))


def _run_units(
    chain: LLMChain,
    units: list[_Unit],
    slots: list[_Slot],
    *,
    tone: str,
    strength: str,
    options: dict[str, Any],
    on_progress: Progress | None,
    stage: str,
    completed: int,
    total: int,
) -> list[_Unit]:
    """Run rewrite calls with bounded concurrency and keep sentence order."""
    if not units:
        return []
    limit = min(_workers(), len(units))
    if limit <= 1:
        results: list[_Unit] = []
        for offset, unit in enumerate(units, start=1):
            results.append(
                _rewrite_unit(
                    chain, unit, slots, tone=tone, strength=strength, options=options
                )
            )
            _emit(
                on_progress,
                stage,
                completed + offset,
                total,
                f"Sentence {completed + offset} of {total}",
            )
        return results

    with ThreadPoolExecutor(max_workers=limit) as pool:
        futures = [
            pool.submit(
                _rewrite_unit,
                chain,
                unit,
                slots,
                tone=tone,
                strength=strength,
                options=options,
            )
            for unit in units
        ]
        results = []
        for offset, future in enumerate(futures, start=1):
            results.append(future.result())
            _emit(
                on_progress,
                stage,
                completed + offset,
                total,
                f"Sentence {completed + offset} of {total}",
            )
    return results


def _report(units: list[_Unit], options: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, unit in enumerate(units, start=1):
        unit.flags = _unit_flags(unit, options)
        rows.append({
            "index": index,
            "source_ids": list(range(unit.start + 1, unit.end + 2)),
            "source": unit.source,
            "text": unit.text,
            "rules": [] if unit.operation == "keep" else [unit.operation],
            "operation": unit.operation,
            "operation_label": label(unit.operation),
            "validator": unit.validator,
            "meaning_score": round(unit.meaning_score, 3),
            "similarity": meaning.similarity(unit.source, unit.text),
            "status": "unchanged" if unit.text == unit.source else "restructured",
            "restructured": unit.text != unit.source,
            "flags": unit.flags,
            "remaining_flags": list(unit.flags),
            "allowed_drop": False,
        })
    return rows


def _meta(
    chain: LLMChain,
    *,
    rounds: int,
    requested: int,
    before: float,
    after: float,
    kept: int,
    total: int,
    operations: dict[str, int],
) -> dict[str, Any]:
    provider = chain.used_provider or (chain.names()[0] if chain.available else "")
    model = chain.used_model
    if not model and chain.providers:
        model = chain.providers[0].model
    return {
        "mode": "online",
        "provider": provider,
        "model": model,
        "provider_order": chain.names(),
        "rounds": rounds,
        "rounds_requested": requested,
        "cache_hits": chain.cache_hits,
        "kept_chunks": kept,
        "density_before": before,
        "density_after": after,
        "sentences_total": total,
        "operations": operations,
        "errors": chain.errors,
    }


def rewrite_document(
    chain: LLMChain,
    text: str,
    *,
    tone: str,
    strength: str,
    intensity: str,
    options: dict[str, Any],
    examples: Iterable[dict[str, Any]] = (),
    target_density: float = 1.0,
    on_progress: Progress | None = None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Plan and rewrite one sentence at a time, then re-humanize flagged ones."""
    requested = passes_for(intensity)
    before = density(text, options)
    parsed, slots = _segments(text)
    if not slots:
        return text, _meta(chain, rounds=0, requested=requested, before=before,
                           after=before, kept=0, total=0, operations={}), []

    _emit(on_progress, "analyze", 0, requested, "Analyzing sentence length and openings")
    analysis = analyze([slot.core for slot in slots], options)
    breaks = {
        index
        for index in range(1, len(slots))
        if slots[index].block_index != slots[index - 1].block_index
    }
    infos = plan(analysis, intensity=intensity, paragraph_breaks=breaks)

    # Build one unit per sentence, except merged short pairs.
    units: list[_Unit] = []
    position = 0
    while position < len(infos):
        info = infos[position]
        if info.operation == "merge" and position + 1 < len(infos):
            pair = infos[position + 1]
            source = f"{slots[position].core} {slots[position + 1].core}"
            units.append(_Unit(start=position, end=position + 1, operation="merge",
                               source=source, text=source))
            position += 2
            continue
        units.append(_Unit(start=position, end=position, operation=info.operation,
                           source=slots[position].core, text=slots[position].core))
        position += 1

    total = len(units)
    operations: dict[str, int] = {}
    for unit in units:
        operations[unit.operation] = operations.get(unit.operation, 0) + 1

    plan_count = sum(1 for unit in units if unit.operation != "keep")
    _emit(
        on_progress,
        "rewrite",
        0,
        max(total, 1),
        f"{plan_count} sentence{'s' if plan_count != 1 else ''} to rewrite",
    )

    editable = [unit for unit in units if unit.operation != "keep"]
    rewritten = _run_units(
        chain,
        editable,
        slots,
        tone=tone,
        strength=strength,
        options=options,
        on_progress=on_progress,
        stage="rewrite",
        completed=0,
        total=max(total, 1),
    )
    by_start = {unit.start: unit for unit in rewritten}
    units = [by_start.get(unit.start, unit) for unit in units]
    current = _assemble(parsed, slots, units)

    # Re-humanize only sentences that still show a signal.
    rounds = 1
    while rounds < requested:
        score = density(current, options)
        if score <= target_density:
            break
        flagged = [unit for unit in units if _unit_flags(unit, options)]
        if not flagged:
            break
        _emit(
            on_progress,
            "rehumanize",
            rounds,
            requested,
            f"Round {rounds + 1} of {requested}: {len(flagged)} flagged",
        )
        retry: list[_Unit] = []
        for unit in flagged:
            retry.append(
                _Unit(
                    start=unit.start,
                    end=unit.end,
                    operation=_rehumanize_operation(unit, options),
                    source=unit.source,
                    text=unit.text,
                )
            )
        results = _run_units(
            chain,
            retry,
            slots,
            tone=tone,
            strength=strength,
            options=options,
            on_progress=on_progress,
            stage="rehumanize",
            completed=0,
            total=len(retry),
        )
        changed = False
        for previous, fresh in zip(flagged, results):
            if fresh.validator == "passed" and fresh.text != previous.text:
                previous.text = fresh.text
                previous.operation = fresh.operation
                previous.validator = "rehumanized:" + fresh.operation
                previous.meaning_score = fresh.meaning_score
                changed = True
        rounds += 1
        current = _assemble(parsed, slots, units)
        if not changed:
            break

    current = _assemble(parsed, slots, units)
    report = _report(units, options)
    operations = {}
    for unit in units:
        operations[unit.operation] = operations.get(unit.operation, 0) + 1
    after = density(current, options)
    meta = _meta(
        chain,
        rounds=rounds,
        requested=requested,
        before=before,
        after=after,
        kept=sum(1 for row in report if row["operation"] == "keep"),
        total=len(report),
        operations=operations,
    )
    meta["analysis"] = analysis.as_dict()
    _emit(on_progress, "done", rounds, requested, "Sentence rewriting finished")
    return current, meta, report


def rewrite_single(
    chain: LLMChain,
    text: str,
    *,
    tone: str,
    strength: str,
    options: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Rewrite one flagged sentence or short passage."""
    parsed, slots = _segments(text)
    if not slots:
        return text, {"mode": "online", "accepted": False, "reasons": ["empty"]}
    source = " ".join(slot.core for slot in slots)
    unit = _Unit(start=0, end=len(slots) - 1, operation="synonym",
                 source=source, text=source)
    refreshed = _rewrite_unit(
        chain, unit, slots, tone=tone, strength=strength, options=options
    )
    meta = {
        "mode": "online",
        "provider": chain.used_provider,
        "model": chain.used_model,
        "rounds": 1,
        "cache_hits": chain.cache_hits,
        "accepted": refreshed.validator == "passed",
        "operation": refreshed.operation,
        "reasons": [] if refreshed.validator == "passed" else [refreshed.validator],
        "errors": chain.errors,
    }
    return (refreshed.text if refreshed.validator == "passed" else text), meta
