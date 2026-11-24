"""Assembler, truncation rejection, provider fallback, paid blocking."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.core.chunking import assemble_outputs, split_into_chunks
from backend.core.humanizer import _run_chunk_protected, create_job, run_job
from backend.db import repository
from backend.providers import catalog
from backend.providers.base import GenerationResult, ProviderFailure
from backend.providers.registry import ConfiguredProvider
from backend.core.prompt import HumanizeOptions


class FakeProvider:
    def __init__(
        self,
        text: str = "Rewritten text.",
        provider_id: str = "pollinations",
        *,
        finish: str = "stop",
        error: ProviderFailure | None = None,
    ) -> None:
        self.text = text
        self.finish = finish
        self.error = error
        self.calls: list[Any] = []
        self.provider_id = provider_id or "pollinations"
        self.model = "gpt-oss-20b"

    async def generate(self, request: Any) -> GenerationResult:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return GenerationResult(
            text=self.text, provider_id=self.provider_id, model_id=self.model, finish_reason=self.finish
        )

    async def health(self) -> tuple[bool, str]:
        return True, "fake"


def _configured(provider_id: str, provider: FakeProvider) -> ConfiguredProvider:
    spec = catalog.get_spec(provider_id)
    assert spec is not None
    return ConfiguredProvider(
        spec=spec,
        provider=provider,  # type: ignore[arg-type]
        source="saved",
        masked_key="••••1234",
        model=provider.model,
        base_url=spec.base_url,
    )


def _make_job(text: str = "Original sentence one. Original sentence two.") -> int:
    return create_job(text, mode="balanced", intensity="medium")


def test_truncated_output_is_rejected_and_retried() -> None:
    job_id = _make_job()
    fake = FakeProvider("cut off", finish="length")
    asyncio.run(run_job(job_id, [_configured("pollinations", fake)]))

    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert "cut off" in str(job["error"]).lower()
    chunks = repository.list_chunks(job_id)
    assert chunks[0]["status"] == "error"
    assert chunks[0]["output_text"] is None


def test_provider_fallback_moves_to_next() -> None:
    job_id = _make_job()
    broken = FakeProvider(error=ProviderFailure("bad key", code="invalid_key"))
    working = FakeProvider("Second provider output.")
    asyncio.run(
        run_job(
            job_id,
            [_configured("pollinations", broken), _configured("ovh", working)],
        )
    )
    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["provider_id"] == "ovh"
    assert working.calls


def test_chunk_with_spans_round_trips() -> None:
    from backend.core.protected_spans import extract_spans

    fake = FakeProvider("Replacement text.")
    text = "Visit https://example.com for details.\n\nBy me at a@b.com now."
    redacted, spans = extract_spans(text)
    assert redacted != text
    # The provider echoes the redacted text back plus new words around it.
    fake.text = redacted + " Replacement text."
    result, _, _ = asyncio.run(_run_chunk_protected(text, "sys", [_configured("pollinations", fake)]))
    assert "https://example.com" in result.text
    assert "a@b.com" in result.text
    assert "[PHRASIA_SPAN_" not in result.text


def test_chunk_fails_when_placeholders_cannot_restore() -> None:
    from backend.core.humanizer import ChunkFailure
    from backend.core.protected_spans import extract_spans

    text = "Read https://example.com please."
    redacted, spans = extract_spans(text)
    fake = FakeProvider(redacted.replace(spans[0].placeholder, ""))
    try:
        asyncio.run(_run_chunk_protected(text, "sys", [_configured("pollinations", fake)]))
    except ChunkFailure as exc:
        assert exc.failure.code == "bad_spans"
    else:
        raise AssertionError("expected ChunkFailure")



def test_assembler_has_no_duplicates_or_gaps() -> None:
    text = "First paragraph here. Second sentence too.\n\nSecond paragraph with a bit more text.\n\nThird."
    chunks = split_into_chunks(text, budget=200)
    outputs = [chunk.text for chunk in chunks]
    pairs = [(chunk.separator, out) for chunk, out in zip(chunks, outputs, strict=True)]
    joined = assemble_outputs(pairs)
    assert joined == text.strip()
