"""Positive and negative cases for every transform rule."""
from __future__ import annotations

import pytest

from backend.engine import rules


def _apply(rule_id: str, sentence: str, **context: object) -> list[str]:
    rule = next(item for item in rules.rules() if item["id"] == rule_id)
    return rules.apply(rule, sentence, **context)


CASES = [
    ("skill-contrast-restatement", "It's not a long delay, it's a short delay.", "The delay is short."),
    ("move-lead-to-end", "Through digital tools, employees can share notes.", "Employees can share notes through digital tools.", "Employees share notes."),
    ("front-adverb", "They should also share notes.", "Also, they should share notes.", "They share notes."),
    ("move-relative-to-front", "Managers need a plan where employees feel heard.", "Where employees feel heard, managers need a plan.", "Managers need a plan."),
    ("move-tail-to-front", " Funding fell, so the plan changed.", "Because funding fell, the plan changed.", "Funding fell."),
    ("split-bridge", "Funding fell, so the plan changed.", "Funding fell. That means the plan changed.", "Funding fell."),
    ("some-others-split", "Some employees may feel alone, while others need time.", "Some employees may feel alone. Others need time.", "Employees need time."),
    ("merge-shared-subject", "Employees shared notes.", "Employees shared notes and employees planned." if False else "Employees shared notes and employees planned.", "Employees rested."),
    ("passive-active", "The report was written by Ada.", "Ada wrote the report.", "Ada wrote the report yesterday."),
    ("noun-phrase-verb", "They make a decision today.", "They decide today.", "They eat lunch."),
    ("opener", "In order to finish, the team worked late.", "To finish, the team worked late.", "The team worked late."),
    ("connective", "Furthermore, the plan worked.", "the plan worked.", "The plan worked."),
    ("contraction", "It is clear.", "It's clear.", "It is clear.", {"tone": "academic"}),
    ("phrase-swap", "They worked in order to finish.", "They rested."),
    ("skill-triad", "The plan covers speed, safety, and cost.", "The plan covers speed and cost."),
    ("skill-passive-needed", "No configuration file needed.", "The file is ready."),
    ("synonym", "This is important.", "This is key.", "This is fine.", {"seed": "abc"}),
]


@pytest.mark.parametrize("case", CASES)
def test_rule_positive_and_negative(case: tuple[object, ...]) -> None:
    rule_id, positive, negative = case[:3]
    options = case[3] if len(case) > 3 and isinstance(case[3], dict) else {}
    context = dict(options)
    if rule_id == "merge-shared-subject":
        assert _apply(rule_id, positive, next="Employees planned."), rule_id
        assert not _apply(rule_id, negative, next=""), rule_id
        return
    assert _apply(rule_id, positive, **context), rule_id
    assert not _apply(rule_id, negative, **context), rule_id
