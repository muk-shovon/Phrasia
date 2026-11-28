"""Deterministic sentence rewriting using our own rules and ranker."""
from __future__ import annotations

import difflib
import re
from collections import Counter
from hashlib import sha256
from typing import Any

from backend.engine import assemble, blocks, clean, plan, protect, ranker, rules, sentences, validators
from backend.engine.skill import apply_skill
from backend.engine.skill import scan as skill_scan
from backend.engine.skill.apply import build_report

_WORD = re.compile(r"[A-Za-z0-9']+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_HEDGE = re.compile(r"\b(may|might|can|could|should|must|would|not|no|never)\b", re.IGNORECASE)
_LEXICAL_SAFETY = {"low"}


def _flags(source: str, candidate: str, similarity: float) -> list[str]:
    flags: list[str] = []
    if _NUMBER.findall(source) != _NUMBER.findall(candidate):
        flags.append("number")
    source_hedges = sorted(match.lower() for match in _HEDGE.findall(validators._normalise(source)))
    candidate_hedges = sorted(match.lower() for match in _HEDGE.findall(validators._normalise(candidate)))
    if source_hedges != candidate_hedges:
        flags.append("meaning")
    if similarity > 0.60:
        flags.append("low-change")
    return flags


def _status(safety: str, rule_id: str) -> str:
    if safety in _LEXICAL_SAFETY and rule_id not in {"front-adverb", "move-lead-to-end"}:
        return "lexical"
    return "restructured"


def _introduces_tell(source: str, candidate: str, options: dict[str, Any]) -> bool:
    before = Counter(tell["id"] for tell in skill_scan.scan(source, options))
    after = Counter(tell["id"] for tell in skill_scan.scan(candidate, options))
    return any(count > before.get(tell_id, 0) for tell_id, count in after.items())


def _validation_source(rule_id: str, source: str) -> str:
    if rule_id != "skill-contrast-restatement":
        return source
    match = re.search(
        r"[,;]\s*((?:it|this|that)(?:'s| is)\s+[^.!?]{2,90}[.!?])$",
        source,
        re.IGNORECASE,
    )
    if not match:
        return source
    value = match.group(1)
    return value[:1].upper() + value[1:]


def _sentence_key(value: str) -> str:
    return " ".join(word.lower() for word in _WORD.findall(value))


def _pieces(text: str) -> list[str]:
    """Sentence contents in block order, without bullet markers or labels."""
    out: list[str] = []
    for block in blocks.parse(text):
        body = block.body if block.label and block.body else block.text
        out.extend(sentences.texts(body))
    return out


def _group_pairs(left: list[str], right: list[str]) -> list[tuple[list[tuple[int, str]], str]]:
    matcher = difflib.SequenceMatcher(
        None, [_sentence_key(item) for item in left], [_sentence_key(item) for item in right],
        autojunk=False,
    )
    groups: list[tuple[list[tuple[int, str]], str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            groups.extend(
                ([(i1 + k + 1, left[i1 + k])], right[j1 + k]) for k in range(i2 - i1)
            )
            continue
        sources = list(enumerate(left[i1:i2], start=i1 + 1))
        outputs = right[j1:j2]
        if not outputs:
            groups.append((sources, ""))
        elif not sources:
            groups.extend(([], output) for output in outputs)
        elif len(outputs) == 1:
            groups.append((sources, outputs[0]))
        else:
            groups.extend(([source], output) for source, output in zip(sources[:len(outputs)], outputs))
            groups.extend(([source], "") for source in sources[len(outputs):])
            groups.extend(([], output) for output in outputs[len(sources):])

    merged: list[tuple[list[tuple[int, str]], str]] = []
    for sources, output in groups:
        if not sources and output and merged:
            previous_sources, previous_output = merged[-1]
            merged[-1] = (previous_sources, f"{previous_output} {output}".strip())
            continue
        merged.append((sources, output))
    return merged


def _realign(
    source: str,
    final: str,
    dropped_by_rule: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Pair source sentences with the final sentences they became."""
    left = _pieces(source)
    right = _pieces(final)
    dropped = {" ".join(str(item["snippet"]).split()) for item in (dropped_by_rule or [])}
    records: list[dict[str, Any]] = []
    for sources, output in _group_pairs(left, right):
        output = output.strip()
        source_text = " ".join(item.strip() for _index, item in sources if item.strip())
        ids = [index for index, item in sources if item.strip()]
        similarity = ranker.similarity(source_text, output) if source_text and output else 0.0
        status = "unchanged" if not source_text or source_text == output else "restructured"
        allowed_drop = not output and " ".join(source_text.split()) in dropped
        records.append({
            "source_ids": ids or [len(records) + 1],
            "source": source_text,
            "text": output,
            "rules": [],
            "similarity": similarity,
            "status": status,
            "restructured": status == "restructured",
            "flags": _flags(source_text, output, similarity) if source_text else [],
            "allowed_drop": allowed_drop,
        })
    return records


def _summarise(records: list[dict[str, Any]]) -> dict[str, int]:
    restructured = sum(1 for record in records if record["status"] == "restructured")
    lexical = sum(1 for record in records if record["status"] == "lexical")
    unchanged = sum(1 for record in records if record["status"] == "unchanged")
    scores = [float(record["similarity"]) for record in records]
    return {
        "sentences_total": len(records),
        "sentences_restructured": restructured,
        "sentences_lexical": lexical,
        "sentences_unchanged": unchanged,
        "unchanged_sentences": unchanged,
        "low_change_sentences": sum(1 for record in records if "low-change" in record["flags"]),
        "average_change_pct": round(100 * sum(1 - score for score in scores) / max(len(scores), 1)),
    }


def _rewrite_offline(
    text: str,
    *,
    tone: str = "casual",
    strength: str = "medium",
    variation: int = 0,
    preserve_formatting: bool = True,
    clean_invisible: bool = True,
    replace_dashes: bool = True,
    straight_quotes: bool = True,
) -> dict[str, Any]:
    """Rewrite text locally, returning the result and per-sentence records."""
    raw = text or ""
    source_text = clean.clean(raw) if clean_invisible else raw
    if not source_text.strip():
        raise ValueError("Text is empty.")
    seed = sha256(f"{source_text}|{variation}".encode("utf-8")).hexdigest()
    options = {"replace_dashes": replace_dashes, "straight_quotes": straight_quotes}
    found = skill_scan.scan(source_text, options)
    source_blocks = blocks.parse(source_text)
    prepared, skill_report = apply_skill(
        assemble.assemble(source_blocks), options, found=found
    )
    parsed = blocks.parse(prepared)
    available = rules.available(strength=strength, tone=tone)
    prepared_ids = {tell["id"] for tell in found} | {
        tell["id"] for tell in skill_scan.scan(prepared, options)
    }
    available = [
        rule for rule in available
        if not (
            (rule["id"] == "skill-triad" and "triad-sentence" not in prepared_ids)
            or (rule["id"] == "skill-passive-needed" and "passive-needed" not in prepared_ids)
            or (rule["id"] == "skill-contrast-restatement" and "contrast-restatement" not in prepared_ids)
            or (rule["id"] == "passive-active" and "passive-by" not in prepared_ids)
        )
    ]
    if skill_report["reason"] == "informal register":
        available = []
    records: list[dict[str, Any]] = []
    block_texts: list[str] = []

    for block in parsed:
        working = block.body if block.label else block.text
        if not working.strip():
            block_texts.append(block.text)
            continue
        pieces = sentences.split(working)
        plain = [piece.strip() for piece in pieces if piece.strip()]
        targets = plan.targets(plain) if preserve_formatting else [11] * len(pieces)
        rewritten_pieces: list[str] = []
        skipped: set[int] = set()

        for index, piece in enumerate(pieces):
            core = piece.rstrip()
            trailing = piece[len(core):]
            if index in skipped:
                rewritten_pieces.append(trailing)
                continue
            if not core.strip():
                rewritten_pieces.append(piece)
                continue

            source_ids = [len(records) + 1]
            masked, spans = protect.extract(core)
            next_masked = ""
            next_core = ""
            if index + 1 < len(pieces):
                next_core = pieces[index + 1].rstrip()
                next_masked, _ = protect.extract(next_core)
            joined_preview = f"{core} {next_core}" if next_core else core
            previous_word = records[-1]["text"].split()[:1] if records else []
            previous = previous_word[0].lower() if previous_word else ""
            target = targets[min(index, len(targets) - 1)] if targets else 11

            candidates: list[tuple[str, str, str, str]] = []
            for rule in available:
                for candidate in rules.apply(
                    rule,
                    masked,
                    seed=f"{seed}:{source_ids[0]}:{rule['id']}",
                    tone=tone,
                    next=next_masked,
                ):
                    restored = protect.restore(candidate, spans)
                    if restored is None:
                        continue
                    validation_source = joined_preview if rule["id"] == "merge-shared-subject" else core
                    validation_source = _validation_source(str(rule["id"]), validation_source)
                    ok, _reasons = validators.validate(
                        validation_source,
                        restored,
                        length_max=1.8 if rule["id"] == "skill-passive-needed" else 1.2,
                    )
                    if not ok or _introduces_tell(validation_source, restored, options):
                        continue
                    status = _status(str(rule["safety"]), str(rule["id"]))
                    candidates.append((restored, str(rule["id"]), status, validation_source))
                    if len(candidates) >= 3:
                        break
                if len(candidates) >= 3:
                    break

            best_text = core
            best_rule = "unchanged"
            best_status = "unchanged"
            best_score = ranker.score(
                core, core, target=target, previous=previous, safety="low", restructured=False
            )
            for candidate, rule_id, status, validation_source in candidates:
                score = ranker.score(
                    validation_source,
                    candidate,
                    target=target,
                    previous=previous,
                    safety=next(
                        (str(item["safety"]) for item in available if item["id"] == rule_id),
                        "low",
                    ),
                    restructured=status == "restructured",
                )
                if score > best_score + 0.0001:
                    best_score = score
                    best_text = candidate
                    best_rule = rule_id
                    best_status = status

            final_text = best_text
            applied_rules = [] if best_rule == "unchanged" else [best_rule]

            joined_source = core
            if best_rule == "merge-shared-subject" and index + 1 < len(pieces):
                following = pieces[index + 1]
                next_core = following.rstrip()
                joined_source = f"{core} {next_core}"
                source_ids.append(source_ids[0] + 1)
                skipped.add(index + 1)
                trailing = following[len(next_core):]
            if not validators.validate(
                _validation_source(best_rule, joined_source),
                final_text,
                length_max=1.8 if best_rule == "skill-passive-needed" else 1.2,
            )[0]:
                joined_source = core
                source_ids = source_ids[:1]
                skipped.discard(index + 1)
                final_text = core
                applied_rules = []
                best_status = "unchanged"

            similarity = ranker.similarity(joined_source, final_text)
            records.append({
                "source_ids": source_ids,
                "source": joined_source,
                "text": final_text,
                "rules": applied_rules,
                "similarity": similarity,
                "status": best_status,
                "restructured": best_status == "restructured",
                "flags": _flags(joined_source, final_text, similarity),
            })
            rewritten_pieces.append(final_text + trailing)

        new_working = "".join(rewritten_pieces)
        if block.label and block.body:
            block_texts.append(block.text.replace(block.body, new_working, 1))
        else:
            block_texts.append(new_working)

    final_text = assemble.assemble(parsed, block_texts)
    remaining = skill_scan.survivors(final_text, found, options)
    report = build_report(
        source_text,
        final_text,
        found,
        remaining,
        dropped_by_rule=skill_report["dropped_by_rule"],
        reason=skill_report["reason"],
    )
    records = _realign(source_text, final_text, skill_report["dropped_by_rule"])
    return {
        "text": final_text,
        "records": records,
        "report": report,
        "summary": _summarise(records),
        "meta": {
            "mode": "offline",
            "provider": "",
            "model": "",
            "provider_order": [],
            "rounds": 0,
            "cache_hits": 0,
            "kept_chunks": 0,
            "density_before": 0.0,
            "density_after": 0.0,
            "fallback_used": False,
            "errors": [],
        },
    }


def _online_rewrite(
    source_text: str,
    *,
    tone: str,
    strength: str,
    intensity: str,
    options: dict[str, Any],
    chain: Any,
    offline_fallback: bool,
    on_progress: Any,
) -> dict[str, Any]:
    """Rewrite with hosted passes, then apply the local safety pass."""
    from backend.engine.llm import LLMUnavailable, rewrite_document
    from backend.engine.llm import retrieval
    from backend.engine.llm import settings as provider_settings

    settings = provider_settings.load_settings()
    examples = retrieval.retrieve(tone, strength, source_text, 4)

    def emit(stage: str, current: int, total: int, message: str) -> None:
        if on_progress is not None:
            try:
                on_progress(stage, current, total, message)
            except Exception:
                pass

    try:
        prepared, llm_meta, sentence_report = rewrite_document(
            chain,
            source_text,
            tone=tone,
            strength=strength,
            intensity=intensity,
            options=options,
            examples=examples,
            target_density=float(settings["target_density"]),
            on_progress=emit,
        )
    except LLMUnavailable:
        raise

    total_passes = int(llm_meta.get("rounds", 1))
    emit("skill", total_passes, total_passes, "Scanning the catalog and applying safe edits")
    found = skill_scan.scan(source_text, options)
    prepared_found = skill_scan.scan(prepared, options)
    final_text, skill_report = apply_skill(prepared, options, found=prepared_found)
    remaining = skill_scan.survivors(final_text, found, options)
    report = build_report(
        source_text,
        final_text,
        found,
        remaining,
        dropped_by_rule=skill_report["dropped_by_rule"],
        reason=skill_report["reason"],
    )
    records = _realign(source_text, final_text, skill_report["dropped_by_rule"])
    _attach_operations(records, sentence_report)
    return {
        "text": final_text,
        "records": records,
        "report": report,
        "summary": _summarise(records),
        "meta": {
            **llm_meta,
            "mode": "online",
            "intensity": intensity,
            "fallback_used": False,
            "examples_used": len(examples),
        },
    }


def _attach_operations(
    records: list[dict[str, Any]], report: list[dict[str, Any]]
) -> None:
    """Copy operation and validator details onto the aligned sentence records."""
    by_source: dict[str, dict[str, Any]] = {}
    for row in report:
        key = _sentence_key(str(row.get("source", "")))
        if key:
            by_source.setdefault(key, row)
    for record in records:
        row = by_source.get(_sentence_key(str(record.get("source", ""))))
        if row is None:
            continue
        record["operation"] = row.get("operation", "keep")
        record["operation_label"] = row.get("operation_label", "Nearly unchanged")
        record["validator"] = row.get("validator", "passed")
        record["meaning_score"] = row.get("meaning_score", 0.0)
        record["rules"] = list(row.get("rules", []))
        remaining = list(row.get("flags", []))
        record["remaining_flags"] = remaining
        record["flags"] = list(dict.fromkeys(record.get("flags", []) + remaining))


def rewrite(
    text: str,
    *,
    tone: str = "casual",
    strength: str = "medium",
    variation: int = 0,
    preserve_formatting: bool = True,
    clean_invisible: bool = True,
    replace_dashes: bool = True,
    straight_quotes: bool = True,
    intensity: str | None = None,
    provider: str = "auto",
    mode: str = "auto",
    offline_fallback: bool = True,
    on_progress: Any = None,
) -> dict[str, Any]:
    """Rewrite online when a provider is configured, otherwise locally.

    ``mode`` accepts ``auto``, ``online`` or ``offline``. In online mode the
    local rule engine stays in the loop as the safety pass and as the fallback.
    """
    level = (intensity or strength or "medium").strip().lower()
    if level not in {"light", "medium", "heavy", "ninja"}:
        level = "medium"
    offline_strength = strength if strength in {"light", "medium", "heavy"} else "heavy"
    local = {
        "tone": tone,
        "strength": offline_strength,
        "variation": variation,
        "preserve_formatting": preserve_formatting,
        "clean_invisible": clean_invisible,
        "replace_dashes": replace_dashes,
        "straight_quotes": straight_quotes,
    }
    options = {"replace_dashes": replace_dashes, "straight_quotes": straight_quotes}

    if mode == "offline":
        return _rewrite_offline(text, **local)

    from backend.engine.llm import build_chain

    chain = build_chain(provider)
    if not chain.available:
        if mode == "online" and not offline_fallback:
            raise ValueError(
                "No hosted provider is configured. Add a key on the Settings page "
                "or enable the offline fallback."
            )
        return _rewrite_offline(text, **local)

    source_text = clean.clean(text or "") if clean_invisible else (text or "")
    if not source_text.strip():
        raise ValueError("Text is empty.")

    try:
        return _online_rewrite(
            source_text,
            tone=tone,
            strength="heavy" if level == "ninja" else level,
            intensity=level,
            options=options,
            chain=chain,
            offline_fallback=offline_fallback,
            on_progress=on_progress,
        )
    except Exception as exc:
        from backend.engine.llm import LLMUnavailable

        if not isinstance(exc, LLMUnavailable):
            raise
        if not offline_fallback:
            raise
        result = _rewrite_offline(text, **local)
        result["meta"] = {
            **result["meta"],
            "fallback_used": True,
            "fallback_reason": "providers unavailable",
            "errors": exc.errors,
        }
        if on_progress is not None:
            try:
                on_progress("fallback", 1, 1, "Hosted providers failed; using the local engine")
            except Exception:
                pass
        return result


def rewrite_sentence(
    text: str,
    *,
    tone: str = "casual",
    strength: str = "medium",
    provider: str = "auto",
    replace_dashes: bool = True,
    straight_quotes: bool = True,
) -> dict[str, Any]:
    """Re-humanize one flagged sentence, online when possible."""
    source = (text or "").strip()
    if not source:
        raise ValueError("Text is empty.")
    options = {"replace_dashes": replace_dashes, "straight_quotes": straight_quotes}
    from backend.engine.llm import build_chain

    chain = build_chain(provider)
    if chain.available:
        from backend.engine.llm import rewrite_single

        try:
            rewritten, meta = rewrite_single(
                chain, source, tone=tone, strength=strength, options=options,
            )
        except Exception:
            rewritten, meta = source, {"mode": "offline", "fallback_used": True}
    else:
        rewritten, meta = source, {"mode": "offline", "fallback_used": False}
    try:
        polished, report = apply_skill(rewritten, options)
    except Exception:
        polished, report = rewritten, {}
    return {
        "text": polished,
        "report": report,
        "meta": meta,
    }
