"""Schema checks for our own local data files."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parents[1] / "backend" / "engine" / "data"
EXPECTED_FILES = {
    "ai_patterns.json", "phrases.json", "ranker.json", "rules.json",
    "synonyms.json", "tones.json", "words.json",
}
FORBIDDEN = [
    "by" + "pass", "un" + "detectable", "pas" + "ses", "water" + "mark",
    "detector" + " score",
]


def _load(name: str):
    text = (DATA_DIR / name).read_text(encoding="utf-8")
    return json.loads(text)


def test_data_files_present_and_utf8() -> None:
    names = {path.name for path in DATA_DIR.glob("*.json")}
    assert names == EXPECTED_FILES
    for name in EXPECTED_FILES:
        assert (DATA_DIR / name).read_text(encoding="utf-8").strip()


def test_no_forbidden_claims_in_data() -> None:
    blob = " ".join(
        (DATA_DIR / name).read_text(encoding="utf-8").lower() for name in EXPECTED_FILES
    )
    for term in FORBIDDEN:
        assert term not in blob


def test_ai_patterns_schema() -> None:
    patterns = _load("ai_patterns.json")
    assert isinstance(patterns, list)
    assert 30 <= len(patterns) <= 60
    assert {item["section"] for item in patterns} == set(range(1, 27))
    ids: set[str] = set()
    for item in patterns:
        assert set(item) == {
            "section", "id", "name", "strength", "tier", "kind", "pattern",
            "action", "skip_contexts", "hint",
        }
        assert item["id"] not in ids
        ids.add(item["id"])
        assert item["kind"] in {"regex", "phrase", "function"}
        assert item["strength"] in {"strong", "normal", "weak"}
        assert item["tier"] in {"A", "B", "C"}
        assert item["action"] in {"rewrite", "drop", "flag"}
        assert isinstance(item["skip_contexts"], list)
        assert item["hint"].strip()
        if item["kind"] == "regex":
            assert item["pattern"].strip()
            re.compile(item["pattern"])
        elif item["kind"] == "phrase":
            assert [p for p in item["pattern"].split("|") if p.strip()]
        else:
            assert not item["pattern"].strip()


def test_phrases_schema() -> None:
    data = _load("phrases.json")
    assert set(data) == {"positions", "phrases"}
    positions = data["positions"]
    assert set(positions) == {"opening", "closing", "anywhere"}
    assert all(isinstance(value, str) and value for value in positions.values())
    ids: set[str] = set()
    for item in data["phrases"]:
        assert set(item) == {"id", "phrase", "replacement", "position", "strength"}
        assert item["id"] not in ids
        ids.add(item["id"])
        assert item["phrase"].strip()
        assert isinstance(item["replacement"], str)
        assert item["position"] in positions
        assert item["strength"] in {"strong", "weak"}


def test_words_schema() -> None:
    words = _load("words.json")
    assert isinstance(words, list)
    assert len(words) >= 25
    seen: set[str] = set()
    for item in words:
        assert set(item) == {"word", "replacement", "part_of_speech", "section", "guard"}
        assert item["word"] not in seen
        seen.add(item["word"])
        assert item["word"].strip()
        assert isinstance(item["replacement"], str)
        assert item["part_of_speech"] in {"noun", "verb", "adjective", "adverb"}
        assert item["section"] == 12
        assert isinstance(item["guard"], list)
    required = {"delve", "crucial", "pivotal", "robust", "landscape"}
    assert required <= seen


def test_tones_schema() -> None:
    data = _load("tones.json")
    assert set(data) == {"rule", "tones"}
    assert "Never invent facts" in data["rule"]
    assert set(data["tones"]) == {"casual", "professional", "academic", "marketing", "storytelling"}
    for name, tone in data["tones"].items():
        assert set(tone) == {"contractions", "connectives", "phrase_sets", "note"}
        assert isinstance(tone["contractions"], bool)
        assert tone["connectives"] and all(isinstance(x, str) for x in tone["connectives"])
        assert tone["phrase_sets"] and all(isinstance(x, str) for x in tone["phrase_sets"])
        assert tone["note"].strip()


def test_rules_schema() -> None:
    rules = _load("rules.json")
    assert isinstance(rules, list) and len(rules) >= 12
    ids: set[str] = set()
    for item in rules:
        assert set(item) == {"id", "trigger", "transform", "safety", "preconditions", "tones", "strengths"}
        assert item["id"] not in ids
        ids.add(item["id"])
        assert item["safety"] in {"low", "medium", "high"}
        assert set(item["strengths"]) <= {"light", "medium", "heavy"}
        assert item["preconditions"] and item["tones"]


def test_synonyms_schema() -> None:
    data = _load("synonyms.json")
    assert set(data) == {"density_cap_per_sentence", "density_cap_per_paragraph", "entries"}
    assert data["density_cap_per_sentence"] >= 1
    assert data["density_cap_per_paragraph"] >= data["density_cap_per_sentence"]
    for entry in data["entries"].values():
        assert set(entry) == {"pos", "replacements"}
        assert entry["replacements"]


def test_ranker_schema() -> None:
    data = _load("ranker.json")
    assert set(data) == {"weights", "risk_penalty"}
    expected = {"structural_distance", "rhythm_fit", "pattern_reduction", "length_window", "rule_risk", "repeated_opening", "fluency", "status_bonus"}
    assert set(data["weights"]) == expected
    assert set(data["risk_penalty"]) == {"low", "medium", "high"}


@pytest.mark.parametrize("name", sorted(EXPECTED_FILES))
def test_each_file_is_valid_json(name: str) -> None:
    assert _load(name) is not None
