"""Deterministic sentence rewriting using our own rules and ranker."""
from __future__ import annotations

import re
from hashlib import sha256
from typing import Any

from backend.engine import assemble, blocks, clean, plan, protect, ranker, rules, sentences, validators

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


def rewrite(
    text: str,
    *,
    tone: str = "casual",
    strength: str = "medium",
    variation: int = 0,
    preserve_formatting: bool = True,
    clean_invisible: bool = True,
) -> dict[str, Any]:
    """Rewrite text locally, returning the result and per-sentence records."""
    raw = text or ""
    source_text = clean.clean(raw) if clean_invisible else raw
    if not source_text.strip():
        raise ValueError("Text is empty.")
    seed = sha256(f"{source_text}|{variation}".encode("utf-8")).hexdigest()
    parsed = blocks.parse(source_text)
    available = rules.available(strength=strength, tone=tone)
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
                    ok, _reasons = validators.validate(validation_source, restored)
                    if not ok:
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
            if final_text != core:
                post_masked, post_spans = protect.extract(final_text)
                swapped = rules.apply(
                    next(item for item in rules.rules() if item["id"] == "word-swap"),
                    post_masked,
                )
                if swapped:
                    restored = protect.restore(swapped[0], post_spans)
                    if restored is not None and validators.validate(core, restored)[0]:
                        final_text = restored
                        if "word-swap" not in applied_rules:
                            applied_rules.append("word-swap")

            joined_source = core
            if best_rule == "merge-shared-subject" and index + 1 < len(pieces):
                following = pieces[index + 1]
                next_core = following.rstrip()
                joined_source = f"{core} {next_core}"
                source_ids.append(source_ids[0] + 1)
                skipped.add(index + 1)
                trailing = following[len(next_core):]
            if not validators.validate(joined_source, final_text)[0]:
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

    result = assemble.assemble(parsed, block_texts)
    restructured = sum(1 for record in records if record["status"] == "restructured")
    lexical = sum(1 for record in records if record["status"] == "lexical")
    unchanged = sum(1 for record in records if record["status"] == "unchanged")
    scores = [float(record["similarity"]) for record in records]
    return {
        "text": result,
        "records": records,
        "summary": {
            "sentences_total": len(records),
            "sentences_restructured": restructured,
            "sentences_lexical": lexical,
            "sentences_unchanged": unchanged,
            "unchanged_sentences": unchanged,
            "low_change_sentences": sum(1 for record in records if "low-change" in record["flags"]),
            "average_change_pct": round(100 * sum(1 - score for score in scores) / max(len(scores), 1)),
        },
    }
