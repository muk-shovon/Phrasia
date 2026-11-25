# Contributing to Phrasia

## Development setup

1. Install Python 3.11-3.13 and Node.js 20 or newer.
2. Create a virtual environment and install `requirements.txt` plus `requirements-dev.txt`.
3. Run `npm ci` in `frontend/`.
4. Start the backend with `python run.py --no-browser` and the frontend dev server with `npm run dev` in a second terminal.

Before opening a pull request, run:

```text
python -m pytest
cd frontend
npm run typecheck
npm run build
```

## Code style

- Use typed Python and keep runtime logic in `backend/`.
- Keep TypeScript strict and avoid unchecked DOM or API assumptions.
- Keep rules deterministic, local, and safe for names, numbers, links, quotations, hedges, and negations.
- Use UTF-8 and the indentation rules in `.editorconfig`.

## Engine rules and data

When adding or changing a rule or catalog entry:

1. Update the relevant file in `backend/engine/` or `backend/engine/data/`.
2. Add a focused test.
3. Add or update a fixture in `tests/fixtures/` when the change affects end-to-end text.
4. Check both a positive case and a protected or unsafe case.

## Pull request checklist

- Python tests and TypeScript type checking are green.
- Every new dependency has a reason recorded in `DECISIONS.md`.
- User-facing text makes no detector-performance claim.
- A maintainer rebuilt `frontend/dist/` if the frontend changed.
- `CHANGELOG.md` includes a line for every user-visible change.

## Reporting a bug

Use the bug-report template. Include the operating system, Python version, exact command, a minimal input that reproduces the issue, expected behavior, and the full error message with private text removed.
