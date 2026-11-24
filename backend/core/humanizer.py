"""Humanization orchestration: chunk, call providers, checkpoint, assemble."""
from __future__ import annotations

import asyncio
import json
import logging
import re

from backend.config import CHUNK_CHARS, MAX_INPUT_CHARS, MAX_WORDS_PER_REQUEST, PROVIDER_TIMEOUT_SECONDS
from backend.core import protected_spans
from backend.core.input_hygiene import clean_invisible_characters
from backend.core.sentence_align import (
    build_alignment, low_change_indices, parse_tagged_output, strip_tags, tag_sentences, validate_tagged,
)
from backend.core.chunking import assemble_outputs, split_into_chunks
from backend.core.prompt import (
    HumanizeOptions,
    build_system_prompt,
    normalise_intensity,
    normalise_mode,
)
from backend.db import repository
from backend.providers.base import GenerationRequest, GenerationResult, ProviderFailure
from backend.providers.registry import ConfiguredProvider, ProviderRegistry

logger = logging.getLogger(__name__)

_RUNNING: set[int] = set()
_TERMINAL = {"completed", "cancelled"}
_MAX_CHUNK_ATTEMPTS = 3


class ChunkFailure(Exception):
    """Raised when every configured provider failed for one chunk."""

    def __init__(self, failure: ProviderFailure, attempts: int) -> None:
        super().__init__(failure.message)
        self.failure = failure
        self.attempts = attempts


def derive_title(text: str, title: str | None) -> str:
    if title and title.strip():
        return title.strip()[:200]
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return "Untitled document"
    return (first_line[:80] + "…") if len(first_line) > 80 else first_line


def create_job(
    text: str,
    *,
    title: str | None = None,
    mode: str = "balanced",
    intensity: str = "medium",
    options: HumanizeOptions | None = None,
    provider_id: str | None = None,
) -> int:
    """Persist a document, its source version and a queued job with chunks."""
    resolved_options = options or HumanizeOptions()
    cleaned = (text or "")
    if resolved_options.clean_invisible:
        cleaned = clean_invisible_characters(cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        raise ValueError("There is no text to humanize.")
    if len(cleaned) > MAX_INPUT_CHARS:
        raise ValueError(
            f"The text is longer than the {MAX_INPUT_CHARS:,} character limit."
        )
    word_count = len(cleaned.split())
    if word_count > MAX_WORDS_PER_REQUEST:
        raise ValueError(
            f"This text is {word_count:,} words. The current limit is {MAX_WORDS_PER_REQUEST:,} words per request. Please shorten it and try again."
        )

    chunks = split_into_chunks(cleaned, budget=CHUNK_CHARS)
    if not chunks:
        raise ValueError("There is no text to humanize.")

    document_id = repository.create_document(
        derive_title(cleaned, title), source_type="pasted"
    )
    source_version_id = repository.add_version(document_id, "source", cleaned)
    job_id = repository.create_job(
        document_id=document_id,
        source_version_id=source_version_id,
        status="queued",
        mode=normalise_mode(mode),
        intensity=normalise_intensity(intensity),
        options_json=json.dumps(
            {
                "preserve_formatting": resolved_options.preserve_formatting,
                "keep_quotes": resolved_options.keep_quotes,
                "deep_humanize": resolved_options.deep_humanize,
                "remove_em_dashes": resolved_options.remove_em_dashes,
                "clean_invisible": resolved_options.clean_invisible,
            }
        ),
        total_chunks=len(chunks),
        provider_id=provider_id or None,
    )
    repository.create_chunks(
        job_id,
        [{"text": chunk.text, "separator": chunk.separator} for chunk in chunks],
    )
    return job_id


def _max_tokens(text: str) -> int:
    estimate = int(len(text) / 3.2) + 400
    return max(768, min(8192, estimate))


def _candidates(job: dict[str, object], providers: list[ConfiguredProvider]) -> list[ConfiguredProvider]:
    requested = job.get("provider_id")
    if isinstance(requested, str) and requested:
        preferred = [item for item in providers if item.spec.id == requested]
        if preferred:
            return preferred + [item for item in providers if item.spec.id != requested]
    return list(providers)


async def _generate_chunk(
    text: str, system: str, providers: list[ConfiguredProvider], temperature: float = 0.4
) -> tuple[GenerationResult, ConfiguredProvider, int]:
    last_error = ProviderFailure(
        "No provider could process this chunk.", code="no_provider"
    )
    attempts = 0
    for configured in providers:
        max_tokens = _max_tokens(text)
        for attempt_no in range(1, _MAX_CHUNK_ATTEMPTS + 1):
            if attempt_no > 1:
                await asyncio.sleep(0.5 * (attempt_no - 1))
            attempts += 1
            request = GenerationRequest(
                text=text,
                system=system,
                model=configured.model,
                max_tokens=max_tokens,
                timeout=PROVIDER_TIMEOUT_SECONDS,
            )
            try:
                result = await configured.provider.generate(request)
            except ProviderFailure as exc:
                last_error = exc
                logger.warning(
                    "provider %s failed (code=%s)", configured.spec.id, exc.code
                )
                break

            if result.finish_reason == "length":
                last_error = ProviderFailure(
                    "The model output was cut off before the chunk finished.",
                    code="truncated",
                    retryable=True,
                )
                max_tokens = min(8192, max_tokens * 2)
                continue
            if result.finish_reason == "blocked":
                last_error = ProviderFailure(
                    "The provider blocked this chunk.", code="blocked"
                )
                break
            if len(result.text.strip()) < 2:
                last_error = ProviderFailure(
                    "The provider returned an empty response.", code="empty_response"
                )
                break
            return result, configured, attempts
    raise ChunkFailure(last_error, attempts)


async def _run_chunk_sentence_aligned(
    text: str,
    system: str,
    providers: list[ConfiguredProvider],
    *,
    intensity: str = "medium",
) -> tuple[str, list[dict[str, Any]], ConfiguredProvider, int]:
    """Generate a chunk using sentence-aligned tagged format."""
    from backend.core.quality_checks import banned_word_hits, flat_rhythm_indices

    sources, tagged_input = tag_sentences(text)
    if not sources:
        raise ChunkFailure(ProviderFailure("Empty chunk.", code="empty_chunk"), 0)
    redacted, spans = protected_spans.extract_spans(tagged_input)
    total_attempts = 0
    max_total = 10
    last_failure = ProviderFailure("Could not generate a valid tagged rewrite.", code="invalid_tags", retryable=True)
    intensity_n = (intensity or "medium").lower()
    do_structure = intensity_n in {"medium", "heavy", "strong"}
    threshold = 0.60

    async def _gen(sys_prompt: str, inp: str = redacted, temperature: float = 0.4):
        nonlocal total_attempts
        res, used_p, att = await _generate_chunk(inp, sys_prompt, providers, temperature=temperature)
        total_attempts += att
        if spans:
            restored = protected_spans.restore_spans(res.text, spans)
            # if restore failed (missing/dup) but input wasn't the redacted tagged form, just return raw
            if restored is None and inp is not redacted:
                return res.text, used_p
            return restored, used_p
        return res.text, used_p

    async def _fact_first(sys_prompt: str):
        # a) extract facts
        extract_sys = "List the facts, numbers, names and constraints in this text as short numbered points. Keep hedges (may/might/should) and negations. Do not reword."
        ext, used_p = await _gen(extract_sys, redacted, temperature=0.2)
        points = ext or tagged_input
        # b) write from points only
        moves = "Required moves: flip clause order, start with a different clause, split one sentence into two, merge with the neighbouring sentence, turn a noun phrase into a clause. Vary moves across sentences."
        write_sys = sys_prompt + "\n\nUse ONLY these points (never the original wording). " + moves + "\nReturn [S#] tagged output covering every source sentence in order."
        restored, used_p2 = await _gen(write_sys, points, temperature=0.9)
        # verify critical source facts present
        if restored:
            src_nums = re.findall(r"\d+(?:[\.,]\d+)?", text)
            out_nums = re.findall(r"\d+(?:[\.,]\d+)?", restored)
            if not all(n in out_nums for n in src_nums):
                return None, used_p2
            src_hedges = re.findall(r"\b(may|might|should|must|can|could|not|no|never|always|usually|often)\b", text, re.I)
            out_low = restored.lower()
            for h in src_hedges:
                if h.lower() not in out_low:
                    return None, used_p2
        return restored, used_p2

    def _parse(restored: str | None):
        if restored is None:
            return None, "bad_spans"
        items = parse_tagged_output(restored)
        ok, reason = validate_tagged(items, len(sources))
        if not ok:
            if re.search(r"[.!??]", restored):
                from backend.core.sentence_align import split_sentences as _ss, TaggedItem as _TI
                plain_parts = _ss(restored)
                if len(plain_parts) == len(sources):
                    items = [_TI(indices=[i + 1], text=t) for i, t in enumerate(plain_parts)]
                    ok, reason = validate_tagged(items, len(sources))
        return (items, "ok") if ok else (None, reason)

    items = None
    used = providers[0]

    # Main path
    if intensity_n in {"heavy", "strong"}:
        try:
            restored, used = await _fact_first(system)
            items, reason = _parse(restored)
            if items is None:
                code = "bad_spans" if reason == "bad_spans" else "invalid_tags"
                last_failure = ProviderFailure(f"Invalid tagged output ({reason}).", code=code, retryable=True)
        except ChunkFailure as exc:
            last_failure = exc.failure
    if items is None:
        for _round in range(3):
            if total_attempts >= max_total:
                break
            try:
                restored, used = await _gen(system)
            except ChunkFailure as exc:
                last_failure = exc.failure
                total_attempts += exc.attempts
                continue
            items, reason = _parse(restored)
            if items is None:
                code = "bad_spans" if reason == "bad_spans" else "invalid_tags"
                last_failure = ProviderFailure(f"Invalid tagged output ({reason}).", code=code, retryable=True)
                continue
            break
    if items is None:
        raise ChunkFailure(last_failure, total_attempts)

    flat_marked: set[int] = set()

    # banned word scan -> retry only affected sentence numbers
    b_hits = banned_word_hits(sources, items)
    if b_hits and total_attempts < max_total:
        bad_tags = ", ".join(f"S{i}" for i in sorted(b_hits.keys()))
        words = ", ".join(sorted({w for ws in b_hits.values() for w in ws}))[:120]
        strong_sys = system + f"\n\nRewrite only {bad_tags}. Replace these words with plain ones: {words}. Keep other sentences unchanged."
        try:
            restored2, used2 = await _gen(strong_sys)
            items2, _ = _parse(restored2)
            if items2:
                items, used = items2, used2
        except ChunkFailure:
            pass

    # rhythm check
    r_hits = flat_rhythm_indices(sources, items)
    if r_hits and total_attempts < max_total:
        r_tags = ", ".join(f"S{i}" for i in r_hits)
        strong_sys = system + f"\n\nRewrite only {r_tags}. Vary the sentence length: mix short and long. Keep other sentences unchanged."
        try:
            restored2, used2 = await _gen(strong_sys)
            items2, _ = _parse(restored2)
            if items2:
                r2 = flat_rhythm_indices(sources, items2)
                items, used = items2, used2
                if r2:
                    flat_marked = set(r2)
        except ChunkFailure:
            pass
    if r_hits and not flat_marked:
        r2 = flat_rhythm_indices(sources, items)
        if r2:
            flat_marked = set(r2)

    # similarity / structure check
    low = set()
    if do_structure:
        low = set(low_change_indices(sources, items, threshold=threshold))
        if low and total_attempts < max_total:
            # one retry with stronger instruction
            low_tags = ", ".join(f"S{i}" for i in sorted(low))
            strong_sys = system + f"\n\nRewrite {low_tags} with a clearly different sentence structure. Do not just swap words."
            try:
                restored2, used2 = await _gen(strong_sys)
                items2, _ = _parse(restored2)
                if items2:
                    low2 = set(low_change_indices(sources, items2, threshold=threshold))
                    # medium fallback: if still >0.6 similar after one retry, try fact-first for those sentences
                    if intensity_n == "medium" and low2 and total_attempts < max_total:
                        try:
                            ff_restored, ff_used = await _fact_first(system + f"\n\nFocus on changing structure for: {', '.join(f'S{i}' for i in sorted(low2))}.")
                            ff_items, _ = _parse(ff_restored)
                            if ff_items:
                                ff_low = set(low_change_indices(sources, ff_items, threshold=threshold))
                                # pick best (fewer low)
                                if len(ff_low) <= len(low2):
                                    items2, used2, low2 = ff_items, ff_used, ff_low
                        except ChunkFailure:
                            pass
                    items, used, low = items2, used2, low2
            except ChunkFailure as exc:
                total_attempts += exc.attempts
                pass

    # verify critical facts/numbers/names/urls/placeholders/hedges present for fact-first? best-effort
    alignment = build_alignment(sources, items, low)
    for a in alignment:
        if any(i in flat_marked for i in a.get("source_indices", [])):
            a["flat_rhythm"] = True
    return strip_tags(items), alignment, used, total_attempts


async def _run_chunk_protected(
    text: str,
    system: str,
    providers: list[ConfiguredProvider],
) -> tuple[GenerationResult, ConfiguredProvider, int]:
    """Backward-compatible wrapper: returns plain text result."""
    plain, _mapping, used, attempts = await _run_chunk_sentence_aligned(text, system, providers)
    return GenerationResult(text=plain, provider_id=used.spec.id, model_id=used.model, finish_reason="stop"), used, attempts


def _fail(job_id: int, message: str, completed: int) -> None:
    repository.update_job(
        job_id, status="failed", error=message, completed_chunks=completed
    )


async def _optional_deep_pass(
    text: str, system: str, provider: ConfiguredProvider
) -> str:
    """One extra LLM pass, only when the owner enabled deep_humanize."""
    redacted, spans = protected_spans.extract_spans(text)
    request = GenerationRequest(
        text=redacted,
        system="Return only the cleaned-up version of this passage.",
        model=provider.model,
        max_tokens=min(8192, _max_tokens(text) + 256),
        timeout=PROVIDER_TIMEOUT_SECONDS,
    )
    try:
        result = await provider.provider.generate(request)
    except ProviderFailure as exc:
        logger.warning("deep pass failed (code=%s)", exc.code)
        return text
    restored = protected_spans.restore_spans(result.text, spans)
    return restored if restored is not None else text


async def run_job(
    job_id: int,
    providers: list[ConfiguredProvider] | None = None,
) -> None:
    """Run or resume a job. Safe to call twice; pending chunks are skipped."""
    if job_id in _RUNNING:
        return
    job = repository.get_job(job_id)
    if job is None or job["status"] in _TERMINAL:
        return

    _RUNNING.add(job_id)
    try:
        available = providers if providers is not None else ProviderRegistry().configured()

        if not available:
            _fail(
                job_id,
                "No provider is configured. Add an API key in Settings first.",
                0,
            )
            return

        candidates = _candidates(job, available)
        options = HumanizeOptions(**json.loads(str(job["options_json"] or "{}")))
        system = build_system_prompt(
            str(job["mode"]), str(job["intensity"]), options
        )
        repository.update_job(job_id, status="running", error=None)
        repository.retry_failed_chunks(job_id)

        chunks = repository.list_chunks(job_id)
        completed = sum(1 for chunk in chunks if chunk["status"] == "completed")

        for chunk in chunks:
            if chunk["status"] == "completed":
                continue
            current = repository.get_job(job_id)
            if current is None or current["status"] == "cancelled":
                return
            try:
                plain_text, alignment, used, attempts = await _run_chunk_sentence_aligned(
                    str(chunk["source_text"]), system, candidates, intensity=str(job["intensity"])
                )
            except ChunkFailure as exc:
                repository.update_chunk(
                    int(chunk["id"]),
                    status="error",
                    attempt_count=int(chunk["attempt_count"]) + exc.attempts,
                    error=exc.failure.message,
                )
                _fail(
                    job_id,
                    f"Chunk {int(chunk['seq']) + 1} of {len(chunks)}: {exc.failure.message}",
                    completed,
                )
                return

            repository.update_chunk(
                int(chunk["id"]),
                status="completed",
                output_text=plain_text,
                mapping_json=json.dumps(alignment),
                attempt_count=int(chunk["attempt_count"]) + attempts,
                error=None,
            )
            repository.record_usage(
                used.spec.id,
                used.model,
                "humanize_chunk",
                len(str(chunk["source_text"] or "")),
                len(plain_text or ""),
            )
            completed += 1
            repository.update_job(
                job_id,
                completed_chunks=completed,
                provider_id=used.spec.id,
                model_id=used.model,
            )

        final_job = repository.get_job(job_id)
        if final_job is None or final_job["status"] == "cancelled":
            return

        final_chunks = repository.list_chunks(job_id)
        joined = assemble_outputs(
            [
                (str(item["separator"] or ""), str(item["output_text"] or ""))
                for item in final_chunks
            ]
        )
        if not joined:
            _fail(job_id, "The provider returned no usable output.", completed)
            return

        if options.deep_humanize and candidates:
            joined = await _optional_deep_pass(joined, system, candidates[0])

        version_id = repository.add_version(
            int(job["document_id"]),
            "humanized",
            joined,
            provider_id=final_job.get("provider_id"),
            model_id=final_job.get("model_id"),
        )
        repository.update_job(
            job_id,
            status="completed",
            result_version_id=version_id,
            completed_chunks=len(final_chunks),
            error=None,
        )
    except Exception:  # pragma: no cover - defensive, still releases the lock
        logger.exception("unexpected failure while running job %s", job_id)
        _fail(job_id, "An unexpected error stopped this job. You can retry it.", 0)
    finally:
        _RUNNING.discard(job_id)


def ensure_resumable(job_id: int) -> bool:
    """Allow retrying a failed/paused/cancelled job without repeating finished work."""
    job = repository.get_job(job_id)
    if job is None:
        return False
    if job["status"] == "completed":
        return False
    repository.update_job(job_id, status="queued", error=None)
    return True
