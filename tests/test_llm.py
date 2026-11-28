"""Hosted rewriting: fallback, validation, caching and learning tables."""
from __future__ import annotations

import json
import re
import time

import pytest

from backend.db import repository
from backend.engine import humanize
from backend.engine.llm import retrieval
from backend.engine.llm.base import LLMError, LLMProvider, LLMUnavailable
from backend.engine.llm.chain import LLMChain
from backend.engine.llm.rewrite import rewrite_chunk


class FixedProvider(LLMProvider):
    def __init__(self, text: str, name: str = "fixed", model: str = "test-model") -> None:
        self.text = text
        self.name = name
        self.model = model
        self.calls = 0
        self.prompts: list[str] = []

    def rewrite(self, system: str, user: str, **_: object) -> str:
        self.calls += 1
        self.prompts.append(user)
        return self.text


class EchoPassageProvider(LLMProvider):
    def __init__(self, name: str = "echo") -> None:
        self.name = name
        self.model = "test-model"
        self.calls = 0
        self.prompts: list[str] = []

    def rewrite(self, system: str, user: str, **_: object) -> str:
        self.calls += 1
        self.prompts.append(user)
        match = re.search(r"<passage>\n(.*?)\n</passage>", user, re.DOTALL)
        return match.group(1) if match else ""


class BrokenProvider(LLMProvider):
    def __init__(self, name: str = "broken") -> None:
        self.name = name
        self.model = "test-model"

    def rewrite(self, system: str, user: str, **_: object) -> str:
        raise LLMError("HTTP 429", status=429, retryable=False, provider=self.name)


def test_chain_tries_the_next_provider() -> None:
    working = FixedProvider("Recovered text.")
    chain = LLMChain([BrokenProvider(), working], use_cache=False)
    completion = chain.complete("system", "user")
    assert completion.text == "Recovered text."
    assert completion.provider == "fixed"
    assert chain.errors and chain.errors[0]["provider"] == "broken"


def test_chain_reports_when_every_provider_fails() -> None:
    chain = LLMChain([BrokenProvider("one"), BrokenProvider("two")], use_cache=False)
    with pytest.raises(LLMUnavailable):
        chain.complete("system", "user")


def test_validator_rejects_a_changed_number() -> None:
    chain = LLMChain([FixedProvider("This report has 99 pages.")], use_cache=False)
    text, accepted, reasons = rewrite_chunk(
        chain,
        "The report has 42 pages.",
        tone="casual",
        strength="medium",
        avoid="none",
    )
    assert accepted is False
    assert text == "The report has 42 pages."
    assert "critical" in reasons


def test_links_and_quotes_never_reach_the_provider() -> None:
    provider = EchoPassageProvider()
    chain = LLMChain([provider], use_cache=False)
    source = 'Visit https://example.com/notes and read "the exact quote" today.'
    text, accepted, _reasons = rewrite_chunk(
        chain, source, tone="casual", strength="medium", avoid="none"
    )
    assert accepted is True
    assert text == source
    assert "https://example.com" not in provider.prompts[0]
    assert "PHRASIA_PROTECT" in provider.prompts[0]


def test_cache_returns_the_same_reply_without_a_second_call() -> None:
    provider = FixedProvider("Cached answer.")
    first = LLMChain([provider]).complete("system", "same question")
    assert first.cached is False
    second = LLMChain([provider]).complete("system", "same question")
    assert second.cached is True
    assert provider.calls == 1


def test_example_retrieval_prefers_matching_words() -> None:
    wanted = repository.add_example_pair(
        tone="casual",
        strength="medium",
        source_text="The quokka crossed the quiet road.",
        rewritten_text="A quokka crossed the quiet road.",
        rating=5,
    )
    rows = retrieval.retrieve("casual", "medium", "quokka road", limit=3)
    assert rows and rows[0]["id"] == wanted


def test_learning_tables_round_trip() -> None:
    feedback_id = repository.add_feedback(
        version_id=None,
        sentence_idx=0,
        action="accepted",
        final_text="Done.",
        operation="split",
    )
    assert feedback_id > 0
    row = repository.list_feedback()[0]
    assert row["action"] == "accepted"
    assert row["operation"] == "split"


def test_online_pipeline_keeps_the_local_safety_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = EchoPassageProvider()
    chain = LLMChain([provider], use_cache=False)
    monkeypatch.setattr("backend.engine.llm.build_chain", lambda preferred="auto": chain)

    result = humanize.rewrite(
        "The policy \u2014 announced today \u2014 starts Friday.",
        intensity="light",
        mode="online",
    )
    assert result["meta"]["mode"] == "online"
    assert result["meta"]["provider"] == "echo"
    assert "\u2014" not in result["text"]
    assert "announced today" in result["text"]


def test_online_pipeline_keeps_an_unsafe_candidate_out(monkeypatch: pytest.MonkeyPatch) -> None:
    chain = LLMChain([FixedProvider("The report has 99 pages.")], use_cache=False)
    monkeypatch.setattr("backend.engine.llm.build_chain", lambda preferred="auto": chain)

    result = humanize.rewrite("The report has 42 pages.", intensity="light", mode="online")
    assert "42" in result["text"]
    assert "99" not in result["text"]
    assert result["meta"]["kept_chunks"] >= 1


def test_provider_failure_falls_back_to_the_local_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    chain = LLMChain([BrokenProvider()], use_cache=False)
    monkeypatch.setattr("backend.engine.llm.build_chain", lambda preferred="auto": chain)

    result = humanize.rewrite(
        "The plan \u2014 ready now \u2014 starts today.",
        intensity="light",
        mode="auto",
    )
    assert result["meta"]["mode"] == "offline"
    assert result["meta"]["fallback_used"] is True
    assert result["meta"]["errors"]


def test_provider_failure_can_be_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    chain = LLMChain([BrokenProvider()], use_cache=False)
    monkeypatch.setattr("backend.engine.llm.build_chain", lambda preferred="auto": chain)

    with pytest.raises(LLMUnavailable):
        humanize.rewrite(
            "The plan starts today.",
            intensity="light",
            mode="online",
            offline_fallback=False,
        )


def test_settings_api_keeps_keys_out_of_responses(client) -> None:
    body = client.get("/api/settings").json()
    assert body["providers"]
    assert all("api_key" not in item for item in body["providers"])
    assert all(item["configured"] is False for item in body["providers"])

    response = client.post(
        "/api/settings/keys",
        json={"provider": "groq", "api_key": "gsk_test_value_1234567890"},
    )
    assert response.status_code == 200
    try:
        listed = client.get("/api/settings").json()
        groq = next(item for item in listed["providers"] if item["id"] == "groq")
        assert groq["configured"] is True
        assert groq["key_source"] == "file"
        assert "gsk_test_value" not in json.dumps(listed)
    finally:
        assert client.delete("/api/settings/keys/groq").status_code == 200


def test_job_endpoint_reports_progress_offline(client) -> None:
    created = client.post(
        "/api/humanize/jobs",
        json={"text": "Employees can share notes.", "mode": "offline"},
    )
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    body: dict = {}
    for _ in range(120):
        body = client.get(f"/api/humanize/jobs/{job_id}").json()
        if body["status"] in {"done", "error"}:
            break
        time.sleep(0.05)
    assert body["status"] == "done", body
    assert body["result"]["rewritten"]
    assert body["result"]["meta"]["mode"] == "offline"


def test_sentence_endpoint_offline_is_safe(client) -> None:
    response = client.post(
        "/api/humanize/sentence",
        json={"text": "Ultimately, this is crucial for teams."},
    )
    assert response.status_code == 200
    body = response.json()
    assert "ultimately" not in body["text"].lower()
    assert body["meta"]["mode"] == "offline"
