"""STEP E3 sentence-aligned humanizer tests (mocked)."""
from __future__ import annotations

import asyncio
from typing import Any

from backend.core.sentence_align import parse_tagged_output, validate_tagged, build_alignment, low_change_indices, meaning_flags
from backend.core.rewrite_diff import diff_from_alignment, style_report
from backend.core import humanizer
from backend.db import repository
from backend.providers import catalog
from backend.providers.base import GenerationResult, ProviderFailure
from backend.providers.registry import ConfiguredProvider

FIXTURE = (
    "Remote work has become a widespread part of how many organizations operate today, so working remotely isn't always easy. "
    "Through digital tools, employees can communicate, share information, and work together even when they're in diverse locations. "
    "Some employees may feel disconnected from their teams, while others struggle to balance work responsibilities with personal life."
)


class SeqFakeProvider:
    def __init__(self, texts: list[str], provider_id: str = "pollinations") -> None:
        self.texts = list(texts)
        self.calls: list[Any] = []
        self.provider_id = provider_id
        self.model = "gpt-oss-20b"
        self.i = 0

    async def generate(self, request: Any) -> GenerationResult:
        self.calls.append(request)
        text = self.texts[min(self.i, len(self.texts) - 1)]
        self.i += 1
        return GenerationResult(text=text, provider_id=self.provider_id, model_id=self.model, finish_reason="stop")

    async def health(self) -> tuple[bool, str]:
        return True, "ok"


def _cfg(p: SeqFakeProvider) -> ConfiguredProvider:
    spec = catalog.get_spec(p.provider_id)
    assert spec
    return ConfiguredProvider(spec=spec, provider=p, source="saved", masked_key="***1234", model=p.model, base_url=spec.base_url)


def test_parse_single_merged_split_tags() -> None:
    single = parse_tagged_output("[S1] Hello there.")
    assert len(single) == 1 and single[0].indices == [1]
    merged = parse_tagged_output("[S1+S2] Combined sentence.")
    assert merged[0].indices == [1, 2]
    split = parse_tagged_output("[S1] First part.\n[S1] Second part.")
    # split into two lines with same tag - parser accepts; validator will see duplication/order issue
    assert len(split) == 2 and split[0].indices == [1] and split[1].indices == [1]


def test_validate_missing_duplicated_order() -> None:
    items = parse_tagged_output("[S1] A.\n[S1] B.")
    ok, _ = validate_tagged(items, 2)
    assert not ok
    items = parse_tagged_output("[S2] B.\n[S1] A.")
    ok, _ = validate_tagged(items, 2)
    assert not ok
    items = parse_tagged_output("[S1] A.")
    ok, _ = validate_tagged(items, 2)
    assert not ok
    items = parse_tagged_output("[S1] A.\n[S2] B.")
    ok, _ = validate_tagged(items, 2)
    assert ok


def test_invalid_tags_trigger_retry() -> None:
    # first invalid, second valid
    fake = SeqFakeProvider(["bad output no tags", "[S1] Rewritten sentence."])
    job_id = humanizer.create_job("Original sentence.")
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    assert len(fake.calls) >= 2


def test_low_change_triggers_retry_then_marks() -> None:
    src = "This is a simple sentence."
    fake = SeqFakeProvider([
        "[S1] This is a simple sentence.",  # too similar
        "[S1] This is a simple sentence.",  # still similar
        "[S1] This is a simple sentence.",  # still similar -> accept but marked
    ])
    job_id = humanizer.create_job(src)
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    chunks = repository.list_chunks(job_id)
    import json
    mapping = json.loads(chunks[0]["mapping_json"])
    assert mapping[0]["low_change"] is True
    assert len(fake.calls) >= 2


def test_hedge_loss_flagged() -> None:
    flags = meaning_flags("Some employees may feel disconnected from their teams.", "Some employees feel disconnected from their teams.")
    assert "meaning" in flags


def test_per_pair_diff_alignment_after_merge() -> None:
    alignment = [{
        "source_indices": [1, 2],
        "source_text": "Short one. Short two.",
        "output_text": "Short one and short two together.",
        "risk_flags": [],
        "low_change": False,
        "similarity": 0.5,
    }]
    segs = diff_from_alignment(alignment)
    assert any(s["type"] == "changed" for s in segs)
    assert all("low_change" in s for s in segs if s.get("type") != "equal" or "sentence_space" not in s)


def test_fixture_paragraph_alignment_and_flags() -> None:
    # mock LLM returns a restructured version with merge of S1+S2? Or normal; we'll do a merge and keep meaning
    out = (
        "[S1+S2] Although remote work is now common in many organizations, it can still be hard, even when digital tools let employees communicate, share information, and collaborate across different locations.\n"
        "[S3] Some employees may feel cut off from their teams, while others find it hard to balance work with personal life."
    )
    fake = SeqFakeProvider([out])
    job_id = humanizer.create_job(FIXTURE)
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    detail = repository.get_job_detail(job_id)
    assert detail["output_text"]
    chunks = repository.list_chunks(job_id)
    import json
    mapping = json.loads(chunks[0]["mapping_json"])
    covered = []
    for m in mapping:
        covered.extend(m["source_indices"])
    assert covered == [1, 2, 3]
    # check style report structure stats
    report = style_report(FIXTURE, detail["output_text"], mapping)
    assert report["structure"]["sentences_total"] == 3
    assert "average_change_pct" in report["structure"]
