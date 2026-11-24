"""Local evaluation over tests/fixtures. Prints one row per fixture."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from backend.engine import humanize, plan, protect, validators

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
_BANNED_PATH = Path(__file__).resolve().parent / "data" / "words.json"
_FIELDS = (
    "fixture", "restructured", "lexical", "unchanged", "mean_similarity",
    "banned_left", "rhythm_met", "validator_rejections", "grammar_flags",
    "meaning_failures", "runtime_ms",
)
_FORBIDDEN = re.compile(r"bypass|undetectable|passes|turnitin|gptzero|copyleaks|quillbot|zerogpt", re.I)


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
        "runtime_ms": round(elapsed, 1),
        "text": result["text"],
    }


def rows() -> list[dict[str, Any]]:
    return [evaluate(path) for path in sorted(FIXTURES.glob("*.txt"))]


def forbidden_hits(text: str) -> list[str]:
    return [match.group(0).lower() for match in _FORBIDDEN.finditer(text)]


def main() -> None:
    data = rows()
    widths = {name: max(len(name), *(len(str(row.get(name, ""))) for row in data)) for name in _FIELDS}
    print("  ".join(name.ljust(widths[name]) for name in _FIELDS))
    for row in data:
        print("  ".join(str(row.get(name, "")).ljust(widths[name]) for name in _FIELDS))


if __name__ == "__main__":
    main()
