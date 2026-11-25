"""Local evaluation over tests/fixtures. Prints one row per fixture."""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from backend.engine import humanize, plan, protect, validators

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
_BANNED_PATH = Path(__file__).resolve().parent / "data" / "words.json"
_FIELDS = (
    "fixture", "restructured", "lexical", "unchanged", "mean_similarity",
    "banned_left", "rhythm_met", "validator_rejections", "grammar_flags",
    "meaning_failures", "sections", "runtime_ms",
)
_BLOCKED = (
    "by" + "pass", "un" + "detectable", "pas" + "ses", "turn" + "itin",
    "gpt" + "zero", "copy" + "leaks", "quill" + "bot", "zero" + "gpt",
)
_FORBIDDEN = re.compile("|".join(map(re.escape, _BLOCKED)), re.I)


def _tone(name: str) -> str:
    for candidate in ("academic", "marketing", "storytelling", "professional", "casual"):
        if candidate in name:
            return candidate
    return "casual"


def _banned_left(text: str) -> int:
    masked, spans = protect.extract(text)
    if not protect.restore(masked, spans):
        return 0
    data = json.loads(_BANNED_PATH.read_text(encoding="utf-8"))
    total = 0
    for item in data:
        word = str(item["word"])
        pattern = r"(?<!\w)" + re.escape(word) + r"(?!\w)"
        total += len(re.findall(pattern, masked, re.IGNORECASE))
    return total


def section_rows(report: dict[str, Any]) -> list[dict[str, int | str]]:
    """Per-section found/fixed/survived/review counts for eval output."""
    review = Counter(int(item["section"]) for item in report["review"])
    return [
        {
            "section": int(item["section"]),
            "name": str(item["name"]),
            "found": int(item["found"]),
            "fixed": int(item["fixed"]),
            "survived": int(item["survived"]),
            "review": review[int(item["section"])],
        }
        for item in report["sections"]
    ]


def _section_text(report: dict[str, Any]) -> str:
    return ", ".join(
        f"§{item['section']} {item['found']}/{item['fixed']}/{item['survived']}/{item['review']}"
        for item in section_rows(report)
    ) or "-"


def evaluate(path: Path, *, variation: int = 0) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    started = time.perf_counter()
    result = humanize.rewrite(
        source, tone=_tone(path.stem), strength="heavy", variation=variation, clean_invisible=True
    )
    elapsed = (time.perf_counter() - started) * 1000
    records = result["records"]
    counts = {name: sum(1 for record in records if record["status"] == name) for name in ("restructured", "lexical", "unchanged")}
    lengths = [plan.word_count(record["text"]) for record in records]
    return {
        "fixture": path.name,
        **counts,
        "mean_similarity": round(sum(float(r["similarity"]) for r in records) / max(len(records), 1), 3),
        "banned_left": _banned_left(result["text"]),
        "rhythm_met": not plan.is_flat_run(lengths),
        "validator_rejections": sum(1 for record in records if not validators.validate(record["source"], record["text"])[0]),
        "grammar_flags": sum(1 for record in records if not validators.grammar_sanity(record["text"])),
        "meaning_failures": sum(
            1 for record in records
            if "meaning" in record["flags"] or "number" in record["flags"]
        ),
        "sections": _section_text(result["report"]),
        "section_rows": section_rows(result["report"]),
        "runtime_ms": round(elapsed, 1),
        "text": result["text"],
    }


def rows() -> list[dict[str, Any]]:
    return [evaluate(path) for path in sorted(FIXTURES.glob("*.txt"))]


def skill_rows() -> list[dict[str, Any]]:
    path = FIXTURES / "skill_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    result: list[dict[str, Any]] = []
    for case in cases:
        rewritten = humanize.rewrite(str(case["before"]), strength="heavy", variation=0)
        result.append({
            "case": str(case["id"]),
            "sections": _section_text(rewritten["report"]),
            "section_rows": section_rows(rewritten["report"]),
        })
    return result


def forbidden_hits(text: str) -> list[str]:
    return [match.group(0).lower() for match in _FORBIDDEN.finditer(text)]


def main() -> None:
    data = rows()
    widths = {name: max(len(name), *(len(str(row.get(name, ""))) for row in data)) for name in _FIELDS}
    print("  ".join(name.ljust(widths[name]) for name in _FIELDS))
    for row in data:
        print("  ".join(str(row.get(name, "")).ljust(widths[name]) for name in _FIELDS))
    print("\nSkill cases (found/fixed/survived/review)")
    for row in skill_rows():
        print(f"{row['case']}: {row['sections']}")


if __name__ == "__main__":
    main()
