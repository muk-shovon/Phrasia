"""Eval-driven guarantees across every fixture."""
from __future__ import annotations

import re
from pathlib import Path

from backend.engine import eval as engine_eval
from backend.engine import humanize

ROOT = Path(__file__).resolve().parents[1]
_BLOCKED = (
    "by" + "pass", "un" + "detectable", "pas" + "ses", "turn" + "itin",
    "gpt" + "zero", "copy" + "leaks", "quill" + "bot", "zero" + "gpt",
    "originality" + ".ai", "sap" + "ling", "ai" + " score",
)
FORBIDDEN = re.compile("|".join(map(re.escape, _BLOCKED)), re.IGNORECASE)


def test_all_fixtures_pass_safety_assertions() -> None:
    for row in engine_eval.rows():
        fixture = row["fixture"]
        assert row["meaning_failures"] == 0, fixture
        assert row["grammar_flags"] == 0, fixture
        assert row["banned_left"] == 0, fixture
        assert row["validator_rejections"] == 0, fixture


def test_rewrite_is_deterministic_for_every_fixture() -> None:
    for path in sorted((ROOT / "tests" / "fixtures").glob("*.txt")):
        source = path.read_text(encoding="utf-8")
        first = humanize.rewrite(source, strength="heavy", variation=0)
        second = humanize.rewrite(source, strength="heavy", variation=0)
        assert first == second, path.name


def test_eval_includes_per_section_skill_counts() -> None:
    remote = next(row for row in engine_eval.rows() if row["fixture"] == "remote_work.txt")
    assert isinstance(remote["section_rows"], list)
    assert all(
        {"section", "name", "found", "fixed", "survived", "review"} == set(item)
        for item in remote["section_rows"]
    )
    skill = engine_eval.skill_rows()
    assert skill
    assert all("section_rows" in row for row in skill)


def test_utf8_round_trip() -> None:
    for path in sorted((ROOT / "tests" / "fixtures").glob("*.txt")):
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        assert text.encode("utf-8") == raw
        result = humanize.rewrite(text, strength="heavy")["text"]
        assert result.encode("utf-8").decode("utf-8") == result


def test_forbidden_words_absent_from_frontend_and_api(client) -> None:
    frontend = ROOT / "frontend" / "src"
    blob = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in frontend.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".css", ".html"}
    )
    assert not FORBIDDEN.findall(blob)

    responses = [
        client.get("/api/health").text,
        client.post("/api/humanize", json={"text": "Employees can share notes."}).text,
        client.post("/api/detector/check", json={"text": "This is a plain sentence."}).text,
        client.post("/api/plagiarism/check", json={"text": "Employees can share notes."}).text,
    ]
    for body in responses:
        assert not FORBIDDEN.findall(body), body[:200]
