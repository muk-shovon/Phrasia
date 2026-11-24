"""Tiny coordinate-descent tuner for our ranker weights."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.engine import humanize, plan, ranker

DATA = Path(__file__).resolve().parent / "data"
_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
_DEFAULT_OUTPUT = DATA / "ranker.json"
_STEP = 0.25


def _objective(weights: dict[str, float]) -> float:
    ranker.set_weights(weights)
    total = 0.0
    for name in ("remote_work.txt", "bullets.txt"):
        path = _FIXTURES / name
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        result = humanize.rewrite(source, tone="casual", strength="heavy", variation=0)
        records = result["records"]
        if not records:
            continue
        risky = sum(1 for record in records if "number" in record["flags"] or "meaning" in record["flags"])
        total += 2.0 * (len(records) - risky) / len(records)
        total += sum(1 for record in records if record["restructured"]) / len(records)
        total += min(ranker.pattern_count(source) - ranker.pattern_count(result["text"]), 10) / 10
        lengths = [plan.word_count(record["text"]) for record in records]
        total += 0.0 if plan.is_flat_run(lengths) else 1.0
    return round(total, 4)


def tune(rounds: int = 1) -> dict[str, float]:
    weights = ranker.weights()
    best = _objective(weights)
    for _ in range(rounds):
        for name in list(weights):
            for direction in (1, -1):
                trial = dict(weights)
                trial[name] = round(trial[name] + direction * _STEP, 4)
                value = _objective(trial)
                if value > best:
                    best, weights = value, trial
    ranker.set_weights(weights)
    return weights


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune ranker weights on local fixtures.")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    args = parser.parse_args()
    weights = tune(max(0, args.rounds))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(_DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    config["weights"] = weights
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
