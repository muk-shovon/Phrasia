"""Build a small stdlib trigram model from local text files."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

_WORD = re.compile(r"[A-Za-z0-9']+")
_DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data" / "lm.json"


def collect(corpus: Path) -> list[str]:
    paths = sorted(corpus.rglob("*.txt")) if corpus.is_dir() else [corpus]
    words: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        words.extend(word.lower() for word in _WORD.findall(path.read_text(encoding="utf-8", errors="replace")))
    return words


def build(corpus: Path) -> dict[str, object]:
    words = collect(corpus)
    counts: Counter[str] = Counter()
    for word in words:
        counts[f"uni:{word}"] += 1
    for first, second in zip(words, words[1:]):
        counts[f"bi:{first} {second}"] += 1
    for first, second, third in zip(words, words[1:], words[2:]):
        counts[f"tri:{first} {second} {third}"] += 1
    return {"vocab": len({word for word in words}), "tokens": len(words), "counts": dict(counts)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a local trigram model (stdlib only).")
    parser.add_argument("--corpus", default="data/corpus", help="Directory or file of UTF-8 text.")
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT), help="Where to write lm.json.")
    args = parser.parse_args()
    corpus = Path(args.corpus)
    if not corpus.exists():
        print(f"Corpus not found: {corpus}")
        return
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build(corpus), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
