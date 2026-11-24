"""Prompt construction covers every mode, intensity and preservation flag."""
from __future__ import annotations

import pytest

from backend.core.prompt import (
    INTENSITIES,
    MODES,
    HumanizeOptions,
    build_system_prompt,
    meta_payload,
    normalise_intensity,
    normalise_mode,
)


@pytest.mark.parametrize("mode", sorted(MODES))
def test_every_mode_is_named_in_the_prompt(mode: str) -> None:
    prompt = build_system_prompt(mode, "medium", HumanizeOptions())
    assert "Return only the rewritten text" in prompt
    assert MODES[mode]["guidance"] in prompt


@pytest.mark.parametrize("intensity", sorted(INTENSITIES))
def test_every_intensity_is_named_in_the_prompt(intensity: str) -> None:
    prompt = build_system_prompt("balanced", intensity, HumanizeOptions())
    assert INTENSITIES[intensity]["guidance"] in prompt


def test_quote_rule_mentions_urls_and_code() -> None:
    prompt = build_system_prompt("balanced", "medium", HumanizeOptions(keep_quotes=True))
    assert "quotation marks" in prompt
    assert "URLs" in prompt


def test_formatting_rule_changes_with_the_flag() -> None:
    keep = build_system_prompt(
        "balanced", "medium", HumanizeOptions(preserve_formatting=True)
    )
    loose = build_system_prompt(
        "balanced", "medium", HumanizeOptions(preserve_formatting=False)
    )
    assert "Preserve the paragraph and line structure" in keep
    assert "may be adjusted slightly" in loose


def test_unknown_values_fall_back_to_defaults() -> None:
    assert normalise_mode("nonsense") == "balanced"
    assert normalise_intensity("extreme") == "medium"


def test_meta_payload_lists_every_option() -> None:
    payload = meta_payload()
    assert [item["id"] for item in payload["modes"]] == list(MODES)
    assert [item["id"] for item in payload["intensities"]] == list(INTENSITIES)
