"""The style signal must stay categorical and honest."""
from __future__ import annotations

from backend.core.detector import DISCLAIMER, analyze

FORMULAIC = (
    "Furthermore, it is important to note that artificial intelligence plays a crucial "
    "role in modern society. Moreover, the utilization of robust machine learning "
    "algorithms facilitates significant advancements in numerous domains. Additionally, "
    "various organizations leverage these optimal technologies to navigate the "
    "complexities of the ever-evolving landscape. In conclusion, it is paramount that we "
    "delve into these robust systems and utilize them to facilitate optimal outcomes. "
    "Furthermore, it is important to note that this trend will continue to be significant."
)

CONVERSATIONAL = (
    "AI is basically everywhere now. My sister uses it to plan meals, and my neighbour "
    "leans on it for lesson plans. Neither of them cares how it works — they just want "
    "the thing to be useful. And honestly? Most days it is. It still gets stuff wrong, "
    "though. Last week it told me a recipe needed two cups of salt. I noticed."
)


def test_label_is_categorical_not_a_score() -> None:
    result = analyze(FORMULAIC)
    assert result["label"] in {"leans formulaic", "mixed", "leans conversational"}
    assert "score" not in result
    assert "percent" not in result
    assert "%" not in str(result)


def test_formulaic_text_is_flagged() -> None:
    assert analyze(FORMULAIC)["label"] == "leans formulaic"


def test_conversational_text_is_not_flagged() -> None:
    assert analyze(CONVERSATIONAL)["label"] == "leans conversational"


def test_disclaimer_is_always_returned() -> None:
    assert analyze(CONVERSATIONAL)["disclaimer"] == DISCLAIMER
    assert "not proof of authorship" in analyze(FORMULAIC)["disclaimer"]


def test_signals_have_names_and_directions() -> None:
    signals = analyze(FORMULAIC)["signals"]
    assert signals
    for signal in signals:
        assert signal["name"]
        assert signal["detail"]
        assert signal["direction"] in {"formulaic", "conversational", "neutral"}
