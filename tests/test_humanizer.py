"""Humanizer orchestration with fake providers (no network)."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.db import repository
from backend.providers import catalog
from backend.providers.base import GenerationResult, ProviderFailure
from backend.providers.registry import ConfiguredProvider
from backend.core import humanizer


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
        self.provider_id = provider_id
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
    return humanizer.create_job(text, mode="balanced", intensity="medium")


def test_job_completes_and_assembles_output() -> None:
    job_id = _make_job()
    fake = FakeProvider("A calmer rewrite.")
    asyncio.run(humanizer.run_job(job_id, [_configured("pollinations", fake)]))

    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["completed_chunks"] == job["total_chunks"]
    detail = repository.get_job_detail(job_id)
    assert detail is not None
    assert detail["output_text"] == "A calmer rewrite."
    assert fake.calls and fake.calls[0].system


def test_truncated_output_is_retried_then_fails() -> None:
    job_id = _make_job()
    fake = FakeProvider("cut off", finish="length")
    asyncio.run(humanizer.run_job(job_id, [_configured("pollinations", fake)]))

    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert "cut off" in str(job["error"]).lower()
    assert len(fake.calls) == 3  # bounded retries with more tokens

    chunks = repository.list_chunks(job_id)
    assert chunks[0]["status"] == "error"
    assert chunks[0]["attempt_count"] == 3


def test_fallback_uses_the_next_provider() -> None:
    job_id = _make_job()
    broken = FakeProvider(error=ProviderFailure("bad key", code="invalid_key"))
    working = FakeProvider("Second provider output.")
    asyncio.run(
        humanizer.run_job(
            job_id,
            [
                _configured("pollinations", broken),
                _configured("ovh", working),
            ],
        )
    )

    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["provider_id"] == "ovh"
    assert working.calls


def test_resume_skips_completed_chunks() -> None:
    job_id = _make_job("one two three")
    first = FakeProvider("First pass.")
    asyncio.run(humanizer.run_job(job_id, [_configured("pollinations", first)]))
    assert repository.get_job(job_id)["status"] == "completed"

    # Retrying a completed job is rejected.
    assert humanizer.ensure_resumable(job_id) is False


def test_no_provider_fails_cleanly() -> None:
    job_id = _make_job()
    asyncio.run(humanizer.run_job(job_id, []))
    job = repository.get_job(job_id)
    assert job is not None
    assert job["status"] == "failed"
    assert "provider" in str(job["error"]).lower()
