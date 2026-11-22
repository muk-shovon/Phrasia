"""Tests for provider ordering and automatic fallback."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.humanizer_service import HumanizerService
from phrasia_domain import (
    HumanizationMode,
    ProviderErrorCategory,
    ProviderTask,
    ProviderTier,
    RewriteIntensity,
    RoutingMode,
)
from providers.base import (
    GenerationProvider,
    GenerationResult,
    ProviderConfig,
    ProviderRegistry,
)
from providers.errors import ProviderError
from providers.router import ProviderRouter


def _options() -> SimpleNamespace:
    return SimpleNamespace(
        mode=HumanizationMode.NATURAL,
        intensity=RewriteIntensity.BALANCED,
        preserve_meaning=True,
        preserve_facts=True,
        preserve_citations=True,
        preserve_formatting=True,
        preserve_quotes=True,
        custom_instruction=None,
        target_language=None,
    )


class QuotaAdapter(GenerationProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    async def generate(self, request):
        raise ProviderError(
            category=ProviderErrorCategory.QUOTA_EXHAUSTED,
            message="You exceeded your current quota",
            status_code=429,
        )

    async def health_check(self):  # pragma: no cover - not used here
        raise NotImplementedError


class GoodAdapter(GenerationProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    async def generate(self, request):
        return GenerationResult(
            output_text="Fallback provider produced this rewritten text.",
            provider_id=self.provider_id,
            model_id=request.model,
            finish_reason="stop",
        )

    async def health_check(self):  # pragma: no cover - not used here
        raise NotImplementedError


def _registry(*specs) -> ProviderRegistry:
    registry = ProviderRegistry()
    for provider_id, priority in specs:
        registry.register(
            ProviderConfig(
                provider_id=provider_id,
                display_name=provider_id,
                task_type=ProviderTask.GENERATION,
                tier=ProviderTier.FREE,
                enabled=True,
                priority=priority,
                default_model="test-model",
            )
        )
    return registry


@pytest.mark.asyncio
async def test_falls_back_when_provider_quota_exhausted() -> None:
    router = ProviderRouter(_registry(("quota", 10), ("backup", 20)))
    service = HumanizerService(
        router=router,
        provider_factories={"quota": QuotaAdapter, "backup": GoodAdapter},
    )
    job, _ = await service.create_job(
        job_id="j1",
        document_id="d1",
        input_text="Short text that needs rewriting.",
        options=_options(),
        routing_mode=RoutingMode.FREE_ONLY,
    )

    more, ok = await service.process_next_chunk(job, use_fallback=True)

    assert ok is True
    assert more is False
    assert job.current_provider == "backup"
    assert job.completed_chunks


@pytest.mark.asyncio
async def test_preferred_provider_is_tried_first() -> None:
    router = ProviderRouter(_registry(("first", 10), ("preferred", 50)))
    service = HumanizerService(
        router=router,
        provider_factories={"first": QuotaAdapter, "preferred": GoodAdapter},
    )
    job, _ = await service.create_job(
        job_id="j2",
        document_id="d1",
        input_text="Another short text for routing.",
        options=_options(),
        routing_mode=RoutingMode.FREE_ONLY,
    )

    more, ok = await service.process_next_chunk(
        job, preferred_provider_id="preferred", use_fallback=True
    )

    assert ok is True
    assert job.current_provider == "preferred"


@pytest.mark.asyncio
async def test_all_providers_failing_marks_chunk_failed() -> None:
    router = ProviderRouter(_registry(("quota-a", 10), ("quota-b", 20)))
    service = HumanizerService(
        router=router,
        provider_factories={"quota-a": QuotaAdapter, "quota-b": QuotaAdapter},
    )
    job, _ = await service.create_job(
        job_id="j3",
        document_id="d1",
        input_text="Text that every provider rejects.",
        options=_options(),
        routing_mode=RoutingMode.FREE_ONLY,
    )

    more, ok = await service.process_next_chunk(job, use_fallback=True)

    assert ok is False
    assert more is True
    assert job.failed_chunks


def test_ordered_providers_puts_preferred_and_fallback_first() -> None:
    router = ProviderRouter(_registry(("a", 10), ("b", 20), ("c", 30)))
    ordered = router.ordered_generation_providers(
        routing_mode=RoutingMode.FREE_ONLY,
        allow_paid=False,
        preferred_provider_id="c",
        fallback_provider_ids=["b"],
    )
    assert [p.provider_id for p in ordered] == ["c", "b", "a"]
