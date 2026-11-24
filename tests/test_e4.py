"""STEP E4 prompt/quality checks tests (mocked)."""
from __future__ import annotations

import asyncio, json
from typing import Any

from backend.core import humanizer
from backend.core.prompt import build_system_prompt, HumanizeOptions
from backend.core.quality_checks import banned_word_hits, flat_rhythm_indices
from backend.core.sentence_align import parse_tagged_output, Sentence, TaggedItem
from backend.db import repository
from backend.providers import catalog
from backend.providers.base import GenerationResult
from backend.providers.registry import ConfiguredProvider


class SeqFake:
    def __init__(self, texts):
        self.texts = list(texts); self.i = 0; self.calls = []; self.provider_id = "pollinations"; self.model = "gpt-oss-20b"
    async def generate(self, request):
        self.calls.append(request)
        t = self.texts[min(self.i, len(self.texts)-1)]; self.i += 1
        return GenerationResult(text=t, provider_id=self.provider_id, model_id=self.model, finish_reason="stop")
    async def health(self): return True, "ok"

def _cfg(p):
    spec = catalog.get_spec(p.provider_id); assert spec
    return ConfiguredProvider(spec=spec, provider=p, source="saved", masked_key="***1234", model=p.model, base_url=spec.base_url)


def test_banned_word_triggers_retry() -> None:
    # first has banned word, second clean
    fake = SeqFake(["[S1] This is a crucial point.", "[S1] This is an important point."])
    job_id = humanizer.create_job("This matters.")
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    assert len(fake.calls) >= 2


def test_banned_word_in_quote_ignored_but_source_replaced() -> None:
    src = [Sentence(1, 'He said "this is crucial".')]
    items = parse_tagged_output('[S1] He said "this is crucial".')
    hits = banned_word_hits(src, items)
    assert 1 not in hits  # inside quote
    src2 = [Sentence(1, "This is crucial.")]
    items2 = parse_tagged_output("[S1] This is crucial to know.")
    hits2 = banned_word_hits(src2, items2)
    assert 1 in hits2  # E6: replace even if in source


def test_flat_rhythm_detection() -> None:
    src = [Sentence(1,"A."), Sentence(2,"B."), Sentence(3,"C.")]
    items = [TaggedItem([1],"This is short one."), TaggedItem([2],"This is short two."), TaggedItem([3],"This is short three.")]
    flat = flat_rhythm_indices(src, items)
    assert flat  # three similar lengths


def test_light_skips_structure_retry() -> None:
    fake = SeqFake(["[S1] This is a simple sentence."])  # same as source, would be low change
    job_id = humanizer.create_job("This is a simple sentence.", intensity="light")
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    assert len(fake.calls) == 1


def test_academic_has_no_contractions_instruction() -> None:
    p = build_system_prompt("academic", "medium", HumanizeOptions())
    assert "few or no contractions" in p.lower()


def test_marketing_prompt_contains_only_source_benefits_rule() -> None:
    p = build_system_prompt("marketing", "medium", HumanizeOptions())
    assert "only benefits stated in the source" in p.lower()


def test_heavy_keeps_paragraph_count() -> None:
    p = build_system_prompt("casual", "heavy", HumanizeOptions())
    assert "keep paragraph count" in p.lower()
