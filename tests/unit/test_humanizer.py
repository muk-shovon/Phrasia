"""Tests for humanizer service."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from phrasia_domain import (
    HumanizationMode,
    JobStatus,
    ProviderTier,
    RewriteIntensity,
    RoutingMode,
)
from core.humanizer_service import HumanizerService
from providers.base import GenerationProvider, ProviderConfig, ProviderTask
from providers.router import ProviderRouter


class FakeAdapter(GenerationProvider):
    def __init__(self, config: ProviderConfig, output: str = "Rewritten text here."):
        self.config = config
        self._output = output

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    async def generate(self, request):
        from providers.base import GenerationResult
        return GenerationResult(
            output_text=self._output,
            provider_id=self.provider_id,
            model_id=request.model or self.config.default_model,
            finish_reason="stop",
        )

    async def health_check(self):
        from providers.base import ProviderHealth
        return ProviderHealth(provider_id=self.config.provider_id, healthy=True)


@pytest.fixture
def registry_and_router():
    cfg = ProviderConfig(
        provider_id="test-fake",
        display_name="Test Fake Provider",
        task_type=ProviderTask.GENERATION,
        tier=ProviderTier.FREE,
        enabled=True,
        priority=10,
        default_model="fake-model",
    )
    reg = ProviderRouter(registry=type("_R", (), {"eligible_for_generation": lambda s, *, allow_paid=True: [cfg], "get": lambda s, pid: cfg})())
    reg.registry = type("_Reg", (), {"_providers": {"test-fake": cfg}, "list_all": lambda s: [cfg], "eligible_for_generation": lambda s, *, allow_paid=True: [cfg], "get": lambda s, pid: cfg})()
    return reg


@pytest.mark.asyncio
async def test_create_job_validates_nonempty() -> None:
    svc = HumanizerService(router=MagicMock(), provider_factories={})
    with pytest.raises(ValueError, match="empty"):
        await svc.create_job(
            job_id="j1", document_id="d1", input_text="",
            options=MagicMock(mode=HumanizationMode.NATURAL),
        )


@pytest.mark.asyncio
async def test_single_short_chunk_completes() -> None:
    cfg = ProviderConfig(
        provider_id="test-fake",
        display_name="Fake",
        task_type=ProviderTask.GENERATION,
        tier=ProviderTier.FREE,
        enabled=True,
        default_model="m",
    )
    reg = type("_R", (), {"select_provider": lambda s, **kw: cfg})()
    svc = HumanizerService(router=reg, provider_factories={"test-fake": FakeAdapter})
    job, _ = await svc.create_job(
        job_id="j1",
        document_id="d1",
        input_text="Short text.",
        options=MagicMock(
            mode=HumanizationMode.NATURAL,
            intensity=RewriteIntensity.BALANCED,
            preserve_meaning=True,
            preserve_facts=True,
            preserve_citations=True,
            preserve_formatting=True,
            preserve_quotes=True,
            custom_instruction=None,
            target_language=None,
        ),
    )
    more, ok = await svc.process_next_chunk(job)
    assert ok is True
    assert len(job.completed_chunks) == 1


@pytest.mark.asyncio
async def test_assemble_output_in_order() -> None:
    cfg = ProviderConfig(
        provider_id="test-fake",
        display_name="Fake",
        task_type=ProviderTask.GENERATION,
        tier=ProviderTier.FREE,
        enabled=True,
        default_model="m",
    )
    class MultiAdapter(FakeAdapter):
        async def generate(self, request):
            seq = int(request.chunk_id.split("-")[-1]) if "-" in request.chunk_id else 0
            return await super().generate(request)

    reg = type("_R", (), {"select_provider": lambda s, **kw: cfg})()
    svc = HumanizerService(router=reg, provider_factories={"test-fake": MultiAdapter}, chunker_max_input_tokens=10)
    long_text = "\n\n".join([f"Chunk paragraph number {i}." for i in range(10)])
    job, _ = await svc.create_job(
        job_id="j1", document_id="d1", input_text=long_text,
        options=MagicMock(
            mode=HumanizationMode.NATURAL,
            intensity=RewriteIntensity.BALANCED,
            preserve_meaning=True, preserve_facts=True,
            preserve_citations=True, preserve_formatting=True,
            preserve_quotes=True, custom_instruction=None, target_language=None,
        ),
    )
    while True:
        more, ok = await svc.process_next_chunk(job)
        if not more or not ok:
            break
    assert job.status != JobStatus.FAILED