# Phrasia — Project Summary

Phrasia is a private, offline writing workspace. It combines a rule-based sentence rewriter, a local plagiarism checker, and a local style-pattern signal. There is no AI call, no API key, and no network access after installation.

## What it does

- **Humanizer** — rewrites text with tones (casual, professional, academic, marketing, storytelling) and strengths (light, medium, heavy). It shows changed wording, meaning-risk markers, pattern counts, and review items.
- **Plagiarism** — compares text against a local reference library using shingles, Jaccard similarity, and difflib.
- **Style Signal** — highlights common writing patterns from the same local catalog. It is a style aid, not proof of authorship.
- **History** — stores documents and versions in local SQLite.

## How the writing pass works

1. Clean invisible characters and normalize spaces.
2. Parse blocks, headings, labels, and bullets.
3. Protect URLs, emails, code, citations, quotes, and measured numbers.
4. Run the skill pass: scan the 26-section catalog, apply safe automatic edits, and record review items.
5. Apply structural sentence rewrites, then validate facts, numbers, names, hedges, negations, grammar, and length.
6. Scan again and assemble the final text.

Automatic edits cover prose dashes, chatbot residue, stock closers, decorative bold, overused words, staged openers, and similar safe cases. Context-dependent cases are left in place and marked for review.

## Skill system

Phrasia includes a local implementation of the `blader/humanizer` skill catalog.

- **26 sections** in `backend/engine/data/ai_patterns.json`.
- **Tier A** — automatic deterministic edits.
- **Tier B** — validator-and-ranker edits.
- **Tier C** — review only; text is not changed.
- **Weak-signal gating** — weak tells need other tells before acting.
- **Dashes** — all prose em/en dashes are replaced when the option is on.
- **Deletion guard** — a deletion is rejected when its span contains a number, name, URL, protected text, quote, hedge, or negation.
- **Informal text** — left unchanged unless it contains enough unrelated tells.

## Key files

- `run.py` — cross-platform launcher with first-run dependency bootstrap.
- `backend/main.py` — FastAPI app and frontend serving.
- `backend/engine/skill/scan.py` — single scanner for all pattern signals.
- `backend/engine/skill/apply.py` — skill pass and report generation.
- `backend/engine/humanize.py` — pipeline orchestration.
- `frontend/src/pages/humanize.ts` — Humanizer UI, diff view, review spans, and options.
- `tests/` — Python tests and fixtures.
- `docs/reference/humanizer-SKILL.md` — source skill reference.

## Requirements

- Python 3.11, 3.12, or 3.13.
- Node.js 20+ only for frontend development.

## Run locally

```powershell
py -3 run.py
```

Open <http://127.0.0.1:8000>. The first run creates `.venv` and installs dependencies.

## Development

```text
python -m pytest
cd frontend
npm run typecheck
npm run build
```

## Documentation

- `README.md` — user and developer guide.
- `DECISIONS.md` — architecture and release decisions.
- `CHANGELOG.md` — change history.
- `CONTRIBUTING.md` — contribution workflow.
- `docs/THIRD_PARTY.md` — third-party credits.
- `docs/reference/humanizer-SKILL.md` — humanizer skill reference.
- `docs/NOTES.md`, `PLAN.md`, `AUDIT.md` — historical refactor notes.

## License

MIT. See `LICENSE` and `docs/THIRD_PARTY.md`.
