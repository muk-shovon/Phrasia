"""Per-sentence pipeline: planning, validation, caching and protection."""
from __future__ import annotations

import re

import pytest

from backend.db import repository
from backend.engine.llm import retrieval
from backend.engine.llm.chain import LLMChain
from backend.engine.llm.base import LLMProvider
from backend.engine.llm.rewrite import passes_for, rewrite_document
from backend.engine.llm.sentence_ops import OPERATIONS, analyze, plan


class SentenceProvider(LLMProvider):
    """A deterministic stand-in for a hosted chat model."""

    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        self.name = "test"
        self.model = "test-model"
        self.calls = 0
        self.rewrite_calls = 0
        self.meaning_calls = 0
        self.prompts: list[tuple[str, str]] = []
        self.replacements = replacements or {
            r"\butilize\b": "use",
            r"\bvery\b": "quite",
        }

    def rewrite(self, system: str, user: str, **_: object) -> str:
        self.calls += 1
        self.prompts.append((system, user))
        if "You check whether two sentences" in system:
            self.meaning_calls += 1
            return "YES"
        self.rewrite_calls += 1
        match = re.search(r"<sentence>\n(.*?)\n</sentence>", user, re.DOTALL)
        value = match.group(1) if match else ""
        for pattern, replacement in self.replacements.items():
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        return value


class EchoSentenceProvider(SentenceProvider):
    def rewrite(self, system: str, user: str, **_: object) -> str:
        self.calls += 1
        self.prompts.append((system, user))
        if "You check whether two sentences" in system:
            self.meaning_calls += 1
            return "YES"
        self.rewrite_calls += 1
        match = re.search(r"<sentence>\n(.*?)\n</sentence>", user, re.DOTALL)
        return match.group(1) if match else ""


def test_segmentation_and_protected_spans_stay_out_of_prompts() -> None:
    provider = EchoSentenceProvider()
    chain = LLMChain([provider], use_cache=False)
    text = (
        "We utilize a tool. Visit https://example.com/notes before you start.\n\n"
        'The report says "the exact quote" and 42 pages.'
    )
    output, meta, report = rewrite_document(
        chain,
        text,
        tone="casual",
        strength="medium",
        intensity="light",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    assert len(report) == 3
    assert "https://example.com/notes" in output
    assert '"the exact quote"' in output
    assert "42 pages" in output
    joined_prompts = "\n".join(user for _system, user in provider.prompts)
    assert "https://example.com" not in joined_prompts
    assert "the exact quote" not in joined_prompts
    assert "PHRASIA_PROTECT" in joined_prompts
    assert meta["sentences_total"] == 3


def test_plan_uses_only_allowed_operations_and_keeps_some_sentences() -> None:
    texts = [
        "The first point is clear and direct.",
        "The second point repeats the same opening.",
        "The third point, which runs on for a while and carries several clauses, explains the idea in a way that could easily be split into two complete sentences.",
        "Short one.",
        "Tiny bit.",
    ]
    analysis = analyze(texts)
    planned = plan(analysis, intensity="medium", paragraph_breaks=set())
    chosen = [item.operation for item in planned]
    assert set(chosen) <= set(OPERATIONS)
    assert "keep" in chosen
    assert any(item.operation in {"split", "opening", "synonym", "punchy"} for item in planned)
    assert all(item.operation != "merge" or item.paired for item in planned)


def test_a_changed_number_is_rejected_and_the_source_is_kept() -> None:
    provider = SentenceProvider({"42": "99"})
    chain = LLMChain([provider], use_cache=False)
    output, _meta, report = rewrite_document(
        chain,
        "The report has 42 pages.",
        tone="casual",
        strength="medium",
        intensity="light",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    assert "42" in output
    assert "99" not in output
    assert report[0]["validator"] != "passed"
    assert report[0]["operation"] == "keep"


def test_second_identical_request_hits_the_cache() -> None:
    provider = SentenceProvider()
    chain = LLMChain([provider], use_cache=True)
    first_output, first_meta, _ = rewrite_document(
        chain,
        "We utilize a very simple plan.",
        tone="casual",
        strength="medium",
        intensity="light",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    calls_after_first = provider.calls
    second_output, second_meta, _ = rewrite_document(
        chain,
        "We utilize a very simple plan.",
        tone="casual",
        strength="medium",
        intensity="light",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    assert second_output == first_output
    assert provider.calls == calls_after_first
    assert second_meta["cache_hits"] >= first_meta["cache_hits"]


def test_retrieval_filters_by_operation() -> None:
    repository.add_example_pair(
        tone="casual",
        strength="medium",
        operation="split",
        source_text="The long sentence had two ideas and it needed a break.",
        rewritten_text="The sentence had two ideas. It needed a break.",
        rating=5,
    )
    repository.add_example_pair(
        tone="casual",
        strength="medium",
        operation="synonym",
        source_text="We utilize a tool.",
        rewritten_text="We use a tool.",
        rating=5,
    )
    rows = retrieval.retrieve("casual", "medium", "sentence ideas", limit=3, operation="split")
    assert rows
    assert all(row["operation"] in {"split", ""} for row in rows)


def test_intensity_maps_to_round_counts() -> None:
    assert passes_for("light") == 1
    assert passes_for("medium") == 2
    assert passes_for("heavy") == 3
    assert passes_for("ninja") == 4


def test_rehumanize_loop_retries_flagged_sentences() -> None:
    provider = SentenceProvider()
    chain = LLMChain([provider], use_cache=False)
    output, meta, report = rewrite_document(
        chain,
        "It's not just fast, it's efficient. It's not just cheap, it's reliable.",
        tone="casual",
        strength="medium",
        intensity="medium",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    assert output
    assert meta["rounds"] >= 1
    assert provider.rewrite_calls >= 2
    assert any("pattern:" in flag for row in report for flag in row["remaining_flags"])


def test_provider_falls_back_to_the_next_ready_provider() -> None:
    from backend.engine.llm.base import LLMError

    class Broken(LLMProvider):
        name = "broken"
        model = "test-model"

        def rewrite(self, system: str, user: str, **_: object) -> str:
            raise LLMError("HTTP 503", status=503, retryable=True, provider="broken")

    chain = LLMChain([Broken(), SentenceProvider()], use_cache=False)
    output, meta, _ = rewrite_document(
        chain,
        "We utilize a very simple plan.",
        tone="casual",
        strength="medium",
        intensity="light",
        options={"replace_dashes": True, "straight_quotes": True},
    )
    assert "broken" in {error["provider"] for error in meta["errors"]}
    assert meta["provider"] == "test"
    assert output
