# Decisions

- Pure Python rewriting: rules, validators, ranker and an optional local trigram model. No network or hosted model.
- Safety first: numbers, names, URLs, code, quotes, hedges and negations are preserved; unsafe candidates are rejected and the source sentence stays.
- One synchronous `/api/humanize` call returns text, sentence records, diff and style check.
- SQLite in `data/phrasia.db` stores documents, versions and references. `require_owner()` is a no-op; the server binds to 127.0.0.1.
- Style signals use our own pattern list only: no verdict, percentage or detector name.
