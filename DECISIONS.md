# Decisions

- Pure Python rewriting: rules, validators, ranker and an optional local trigram model. No network or hosted model.
- Safety first: numbers, names, URLs, code, quotes, hedges and negations are preserved; unsafe candidates are rejected and the source sentence stays.
- One synchronous `/api/humanize` call returns text, sentence records, diff and style check.
- SQLite in `data/phrasia.db` stores documents, versions and references. `require_owner()` is a no-op; the server binds to 127.0.0.1.
- Style signals use our own pattern list only: no verdict, percentage or detector name.
- `ai_patterns.json` is the single catalog; the Humanizer, Style check and Style Signal page all call `skill.scan()`.
- Tier A is deterministic editing, tier B is validator-and-ranker editing, and tier C is review only. Section 26 is skipped because the app has no thread context.
- Sections 1–5 and 22 act on one sighting. A weak signal needs two other sections in its paragraph or three sightings in the document.
- With Replace dashes enabled, every prose em/en dash is replaced even when it is the only signal; code, links and paths stay protected.
- A deletion is recorded by rule and is rejected when its span contains a number, name, link, protected text, quote, hedge or negation.

## Public release defaults

- The simplest end-user path is `python run.py`. When dependencies are unavailable, the launcher creates `.venv`, installs `requirements.txt`, and restarts itself with that environment through a subprocess.
- `frontend/dist/` is committed deliberately. It is generated release output, but this exception lets users run the app with Python alone; Node.js remains a contributor requirement.
- Runtime and development dependencies use compatible ranges. The installed local versions set the lower bounds, and the next major versions are excluded.
- MIT is the default project license.
- Generic generated and runtime files use `.gitignore`; project-specific local-only files use the private `.git/info/exclude` file.
- CI checks Windows and Linux with Python 3.11 and 3.13 plus Node.js 20, running the Python and frontend validation commands on pushes and pull requests.
