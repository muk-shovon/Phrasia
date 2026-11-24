"""STEP E6 tests (mocked)."""
from __future__ import annotations

import asyncio, json
from typing import Any

from backend.core import humanizer
from backend.core.rewrite_diff import diff_segments, _risk
from backend.core.quality_checks import banned_word_hits
from backend.core.sentence_align import Sentence, parse_tagged_output
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


def test_banned_word_in_source_is_replaced() -> None:
    src = [Sentence(1, "Slowly but surely, this is crucial.")]
    items = parse_tagged_output("[S1] Slowly but surely, this is crucial.")
    hits = banned_word_hits(src, items)
    assert 1 in hits
    assert "crucial" in hits[1] or "slowly but surely" in [h.lower() for h in hits[1]]


def test_whitespace_and_punctuation_only_diff_ignored() -> None:
    segs = diff_segments("Hello  world,  test.", "Hello world test")
    # should be treated as equal/punctuation-only ignored
    assert not any(s["type"] == "changed" and s.get("risk") != "none" for s in segs)
    assert all(s["type"] == "equal" for s in segs) or sum(1 for s in segs if s["type"]=="changed")==0


def test_equivalence_table_no_meaning_flag() -> None:
    assert _risk("can do it", "is able to do it", "can do it") == "none"
    assert _risk("because it works", "since it works", "because it works") == "none"
    assert _risk("only one", "just one", "only one") == "none"


def test_hedge_missing_flags_meaning() -> None:
    assert _risk("may feel", "feel", "Some employees may feel disconnected") == "meaning"


def test_fact_first_heavy_path_runs() -> None:
    # heavy should try fact-first: extract then write
    extract = "1. Remote work is widespread. 2. It is not always easy."
    write = "[S1] Many organizations now use remote work.\n[S2] It can still be hard."
    fake = SeqFake([extract, write])
    job_id = humanizer.create_job("Remote work is widespread. It is not always easy.", intensity="heavy")
    asyncio.run(humanizer.run_job(job_id, [_cfg(fake)]))
    job = repository.get_job(job_id)
    assert job["status"] == "completed"
    assert len(fake.calls) >= 2


def test_utf8_round_trip() -> None:
    text = "Caf? ? na?ve r?sum?? Yes."
    segs = diff_segments(text, text)
    assert isinstance(segs, list)
