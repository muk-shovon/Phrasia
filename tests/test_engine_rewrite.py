"""End-to-end deterministic rewriting with the local engine."""
from __future__ import annotations

from pathlib import Path

from backend.core import humanizer
from backend.core.rewrite_diff import diff_from_alignment
from backend.engine import humanize, train, tune, validators
from backend.engine import ranker

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_same_input_gives_same_output() -> None:
    text = (FIXTURES / "remote_work.txt").read_text(encoding="utf-8")
    first = humanize.rewrite(text, tone="casual", strength="heavy", variation=0)
    second = humanize.rewrite(text, tone="casual", strength="heavy", variation=0)
    assert first == second
    assert first["text"] != text


def test_heavy_restructures_remote_work_without_validator_failures() -> None:
    text = (FIXTURES / "remote_work.txt").read_text(encoding="utf-8")
    result = humanize.rewrite(text, tone="casual", strength="heavy", variation=0)
    records = result["records"]
    assert len(records) == 6
    assert result["summary"]["sentences_restructured"] / len(records) >= 0.70
    for record in records:
        ok, reasons = validators.validate(record["source"], record["text"])
        assert ok, reasons
        assert "number" not in record["flags"]
        assert "meaning" not in record["flags"]


def test_variation_changes_seed_deterministically() -> None:
    text = "Through digital tools, employees can share notes."
    first = humanize.rewrite(text, strength="heavy", variation=0)
    second = humanize.rewrite(text, strength="heavy", variation=1)
    assert first["text"] == humanize.rewrite(text, strength="heavy", variation=0)["text"]
    assert isinstance(second["text"], str)


def test_bullets_keep_markers() -> None:
    text = (FIXTURES / "bullets.txt").read_text(encoding="utf-8")
    result = humanize.rewrite(text, strength="heavy")
    lines = [line for line in result["text"].splitlines() if line.strip()]
    assert len(lines) == 3
    assert all(line.startswith("• ") for line in lines)
    assert all(line.count(":") >= 1 for line in lines)


def test_quotes_urls_and_numbers_are_untouched() -> None:
    text = 'Read https://example.com/a and 3 hours. She said "this must stay" today.'
    result = humanize.rewrite(text, strength="heavy")
    assert "https://example.com/a" in result["text"]
    assert "3 hours" in result["text"]
    assert '"this must stay"' in result["text"]


def test_may_feel_never_becomes_feel() -> None:
    text = "Some employees may feel alone, while others need time."
    result = humanize.rewrite(text, strength="heavy")
    assert "may feel" in result["text"]
    assert " may " in result["text"]


def test_train_and_tune_are_local(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.txt").write_text("Employees share notes. Managers read notes.", encoding="utf-8")
    output = tmp_path / "lm.json"
    train.build(corpus)
    model = train.build(corpus)
    assert model["tokens"] > 0
    output.write_text(__import__("json").dumps(model), encoding="utf-8")

    weights = tune.tune(rounds=0)
    assert set(weights) == set(ranker.weights())


def test_diff_supports_merge_and_split() -> None:
    merged = humanizer.humanize("Employees shared notes. Employees planned changes.", strength="heavy")
    assert merged["alignment"][0]["source_indices"] == [1, 2]
    merged_segments = diff_from_alignment(merged["alignment"])
    assert any(segment.get("sentence_start") for segment in merged_segments)

    split = humanizer.humanize("Some employees may feel alone, while others need time.", strength="heavy")
    assert "may feel" in split["text"]
    segments = diff_from_alignment(split["alignment"])
    assert sum(1 for segment in segments if segment.get("sentence_start")) >= 1
