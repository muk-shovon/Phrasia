"""Fixture-driven checks adapted from the credited skill examples."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.engine import humanize
from backend.engine.skill import apply, scan

CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "skill_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", [item for item in CASES if item["mode"] == "exact"], ids=lambda item: item["id"])
def test_clear_examples_match_expected_text(case: dict[str, object]) -> None:
    rewritten, report = apply.apply_skill(str(case["before"]))
    assert rewritten == case["after"]
    assert report["fixed"] > 0


@pytest.mark.parametrize("case", [item for item in CASES if item["mode"] == "gone"], ids=lambda item: item["id"])
def test_other_tier_a_tells_are_removed(case: dict[str, object]) -> None:
    rewritten, _report = apply.apply_skill(str(case["before"]))
    assert not any(tell["section"] == case["section"] for tell in scan.scan(rewritten, gated=False))
    lower = rewritten.lower()
    assert all(str(word).lower() in lower for word in case.get("preserve", []))


@pytest.mark.parametrize("case", [item for item in CASES if item["mode"] == "pipeline"], ids=lambda item: item["id"])
def test_tier_b_fixture_uses_full_pipeline(case: dict[str, object]) -> None:
    result = humanize.rewrite(str(case["before"]), strength="heavy")
    assert not any(tell["section"] == case["section"] for tell in scan.scan(result["text"], gated=False))
    lower = result["text"].lower()
    assert all(str(word).lower() in lower for word in case.get("preserve", []))


@pytest.mark.parametrize("case", [item for item in CASES if item["mode"] == "review"], ids=lambda item: item["id"])
def test_tier_c_fixture_is_unchanged(case: dict[str, object]) -> None:
    source = str(case["before"])
    rewritten, report = apply.apply_skill(source)
    assert rewritten == source
    assert any(item["section"] == case["section"] for item in report["review"])


def test_register_context_and_weak_fixtures_hold() -> None:
    for case in CASES:
        if case["mode"] not in {"informal", "protected", "weak"}:
            continue
        source = str(case["before"])
        result = humanize.rewrite(source, strength="heavy")
        assert result["text"] == source, case["id"]
        if case["mode"] == "informal":
            assert result["report"]["reason"] == "informal register"
