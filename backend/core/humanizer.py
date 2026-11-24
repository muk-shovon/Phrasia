"""Humanization orchestration: chunk, call providers, checkpoint, assemble."""
from __future__ import annotations

import asyncio
import json
import logging

from backend.config import CHUNK_CHARS, MAX_INPUT_CHARS, PROVIDER_TIMEOUT_SECONDS
from backend.core import protected_spans
from backend.core.chunking import assemble_outputs, split_into_chunks
from backend.core.prompt import (
    HumanizeOptions,
    build_system_prompt,
    normalise_intensity,
    normalise_mode,
)
from backend.db import repository
from backend.providers import catalog
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
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("There is no text to humanize.")
    if len(cleaned) > MAX_INPUT_CHARS:
        raise ValueError(
            f"The text is longer than the {MAX_INPUT_CHARS:,} character limit."
        )

    resolved_options = options or HumanizeOptions()
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
    text: str,
    system: str,
    providers: list[ConfiguredProvider],
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


async def _run_chunk_protected(
    text: str,
    system: str,
    providers: list[ConfiguredProvider],
) -> tuple[GenerationResult, ConfiguredProvider, int]:
    """Generate a chunk after masking protected spans.

    Spans are restored exactly; if any come back missing or duplicated, the
    chunk is retried (raised as ChunkFailure).
    """
    redacted, spans = protected_spans.extract_spans(text)
    result, used, attempts = await _generate_chunk(redacted, system, providers)
    restored = protected_spans.restore_spans(result.text, spans)
    if restored is None:
        raise ChunkFailure(
            ProviderFailure(
                "The provider dropped or duplicated a protected span. The chunk was not saved.",
                code="bad_spans",
                retryable=True,
            ),
            attempts,
        )
    result.text = restored
    return result, used, attempts


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

        if not catalog.model_allowed(
            str(job.get("provider_id") or ""), str(job.get("model_id") or "")
        ):
            _fail(
                job_id,
                "This model is paid and paid models are disabled. Enable "
                "PAID_MODELS_ENABLED or pick a free model in Settings.",
                0,
            )
            return

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

        chunks = repository.list_chunks(job_id)
        completed = sum(1 for chunk in chunks if chunk["status"] == "completed")

        for chunk in chunks:
            if chunk["status"] == "completed":
                continue
            current = repository.get_job(job_id)
            if current is None or current["status"] == "cancelled":
                return
            try:
                result, used, attempts = await _run_chunk_protected(
                    str(chunk["source_text"]), system, candidates
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
                output_text=result.text,
                attempt_count=int(chunk["attempt_count"]) + attempts,
                error=None,
            )
            completed += 1
            repository.update_job(
                job_id,
                completed_chunks=completed,
                provider_id=used.spec.id,
                model_id=result.model_id or used.model,
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
