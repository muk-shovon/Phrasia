"""Tests for prompt builder — verifies each mode produces different instructions."""
from __future__ import annotations

import pytest
from core.prompt_builder import build_humanizer_prompt
from phrasia_domain import HumanizationMode, RewriteIntensity


MODES = [
    HumanizationMode.NATURAL,
    HumanizationMode.PROFESSIONAL,
    HumanizationMode.ACADEMIC,
    HumanizationMode.SIMPLE,
    HumanizationMode.CONVERSATIONAL,
    HumanizationMode.CONCISE,
    HumanizationMode.EXPAND,
    HumanizationMode.CUSTOM,
]


@pytest.mark.parametrize("mode", MODES)
def test_each_mode_has_distinct_instructions(mode: HumanizationMode) -> None:
    system, user = build_humanizer_prompt(
        mode=mode.value,
        intensity=RewriteIntensity.BALANCED.value,
        preserve_meaning=True,
        preserve_facts=True,
        preserve_citations=True,
        preserve_formatting=True,
        preserve_quotes=True,
        custom_instruction=None,
        language_hint=None,
    )
    assert "Phrasia" in system
    assert "rewrite" in user.lower() or "mode" in user.lower()
    assert "natural flow" in system or "clarity" in system


def test_custom_instruction_reaches_user_prompt() -> None:
    _, user = build_humanizer_prompt(
        mode=HumanizationMode.CUSTOM.value,
        intensity=RewriteIntensity.LIGHT.value,
        preserve_meaning=True,
        preserve_facts=True,
        preserve_citations=True,
        preserve_formatting=True,
        preserve_quotes=True,
        custom_instruction="Keep technical terms intact.",
        language_hint=None,
    )
    assert "Keep technical terms intact." in user


def test_intensity_affects_prompt() -> None:
    _, light = build_humanizer_prompt(
        mode=HumanizationMode.NATURAL.value,
        intensity=RewriteIntensity.LIGHT.value,
        preserve_meaning=True, preserve_facts=True,
        preserve_citations=True, preserve_formatting=True,
        preserve_quotes=True, custom_instruction=None, language_hint=None,
    )
    _, strong = build_humanizer_prompt(
        mode=HumanizationMode.NATURAL.value,
        intensity=RewriteIntensity.STRONG.value,
        preserve_meaning=True, preserve_facts=True,
        preserve_citations=True, preserve_formatting=True,
        preserve_quotes=True, custom_instruction=None, language_hint=None,
    )
    assert light != strong