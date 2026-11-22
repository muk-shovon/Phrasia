"""Tests for human-likeness improvements (prompt v2, cleanup, deep pass)."""
from __future__ import annotations

import pytest

from core.humanizer_postprocess import apply_human_touch
from core.humanizer_service import HumanizerService
from core.prompt_builder import build_dehumanize_prompt, build_humanizer_prompt
from phrasia_domain import (
    HumanizationMode,
    HumanizationOptions,
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
from providers.router import ProviderRouter


def _opts(**overrides):
    values = {
        "mode": HumanizationMode.NATURAL,
        "intensity": RewriteIntensity.BALANCED,
        "deep_humanize": False,
    }
    values.update(overrides)
    return HumanizationOptions(**values)


def test_prompt_v2_contains_human_signature_rules() -> None:
    system, user = build_humanizer_prompt(
        mode="natural",
        intensity="strong",
        preserve_meaning=True,
        preserve_facts=True,
        preserve_citations=True,
        preserve_formatting=True,
        preserve_quotes=True,
        custom_instruction=None,
        language_hint=None,
    )
    assert "HUMAN WRITING STYLE" in system
    assert "Vary sentence length sharply" in system
    assert "furthermore" in system.lower()
    assert "delve" in system.lower()
    assert "Rewrite aggressively" in user


def test_dehumanize_prompt_is_a_distinct_second_pass() -> None:
    system, user = build_dehumanize_prompt()
    assert "machine-written" in system
    assert "Draft:" in user
    assert "fact" in system.lower()


def test_cleanup_strips_stacked_leading_phrases() -> None:
    text = "Furthermore, it is important to note that this matters."
    result = apply_human_touch(text, mode="natural", intensity="balanced")
    assert result == "This matters."
    assert "Furthermore" not in result
    assert "important to note" not in result


def test_cleanup_uses_contractions_and_plain_words() -> None:
    text = "It is clear that we utilize robust tools in order to work."
    result = apply_human_touch(text, mode="conversational", intensity="balanced")
    assert "It's clear" in result
    assert "use strong tools" in result
    assert "utilize" not in result
    assert "in order to" not in result


def test_cleanup_keeps_formal_register_in_academic_mode() -> None:
    text = "It is not clear that this does not work."
    result = apply_human_touch(text, mode="academic", intensity="light")
    assert "doesn't" not in result
    assert "It is not clear" in result


class TwoPassAdapter(GenerationProvider):
    """Returns a different draft on the second call."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.calls: list[str] = []

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    async def generate(self, request):
        self.calls.append(request.system_instruction)
        if len(self.calls) == 1:
            return GenerationResult(
                output_text="Furthermore, it utilizes robust methods.",
                provider_id=self.provider_id,
                model_id=request.model,
                finish_reason="stop",
            )
        return GenerationResult(
            output_text="It uses strong methods, and that matters.",
            provider_id=self.provider_id,
            model_id=request.model,
            finish_reason="stop",
        )

    async def health_check(self):
        raise NotImplementedError


def _service(adapter):
    registry = ProviderRegistry()
    registry.register(
        ProviderConfig(
            provider_id="fake",
            display_name="fake",
            task_type=ProviderTask.GENERATION,
            tier=ProviderTier.FREE,
            enabled=True,
            priority=1,
            default_model="m",
        )
    )
    return HumanizerService(ProviderRouter(registry), {"fake": lambda config: adapter})


@pytest.mark.asyncio
async def test_deep_pass_uses_second_result_when_enabled() -> None:
    adapter = TwoPassAdapter(ProviderConfig(
        provider_id="fake", display_name="fake",
        task_type=ProviderTask.GENERATION, tier=ProviderTier.FREE,
    ))
    service = _service(adapter)
    job, _ = await service.create_job(
        job_id="j",
        document_id="d",
        input_text="Short sentence about methods.",
        options=_opts(deep_humanize=True),
        routing_mode=RoutingMode.FREE_ONLY,
    )
    more, ok = await service.process_next_chunk(job, use_fallback=True)

    assert ok is True
    assert len(adapter.calls) == 2
    assert "machine-written" in adapter.calls[1]
    assert job.completed_chunks["chunk-0000"] == "It uses strong methods, and that matters."


@pytest.mark.asyncio
async def test_single_pass_when_deep_disabled() -> None:
    adapter = TwoPassAdapter(ProviderConfig(
        provider_id="fake", display_name="fake",
        task_type=ProviderTask.GENERATION, tier=ProviderTier.FREE,
    ))
    service = _service(adapter)
    job, _ = await service.create_job(
        job_id="j",
        document_id="d",
        input_text="Short sentence about methods.",
        options=_opts(deep_humanize=False),
        routing_mode=RoutingMode.FREE_ONLY,
    )
    await service.process_next_chunk(job, use_fallback=True)

    assert len(adapter.calls) == 1
    assert "uses strong methods" in job.completed_chunks["chunk-0000"]
