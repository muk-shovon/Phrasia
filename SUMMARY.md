# Phrasia summary

Phrasia is an **online-first writing workspace with offline fallback**. It rewrites text sentence by sentence using a hosted language model when a provider key exists, and always keeps the local deterministic rule engine for pre/post-processing, validation, and a complete offline fallback. No local ML model is downloaded or run.

## Online-first pipeline

For each request the Humanizer:

1. Cleans invisibles; splits paragraphs, then sentences; protects numbers, names, URLs, emails, code, citations and quoted lines as `[PHRASIA_PROTECT_N]`.
2. Analyzes per sentence (length, opening, pattern hits) and per text (burstiness, repeated openers, hedge/quantifier density, pronoun mix).
3. Plans one operation per sentence, only: word/phrase swap, clause reorder, split, merge adjacent pair, new opening, shorter punchy rewrite, or nearly unchanged. Never changes active↔passive voice. Targets natural short/medium/long mix.
4. Rewrites **one sentence or adjacent pair per provider call**. Concurrency ~4, backoff retries, provider fallback (`429`/`5xx`/timeout → next ready provider → offline rule engine), cache keyed by `(sentence, operation, tone, strength)`.
5. Validates critical facts, negations, hedges, placeholders, grammar, length; runs a cheap meaning check; retries once stricter; otherwise keeps the original sentence.
6. Rescans whole text; re-humanizes only flagged sentences up to `light=1`, `medium=2`, `heavy=3`, `ninja=4` rounds; stops early.
7. Restores protected spans; runs the local skill pass; returns per-sentence report: original, final, operation, validator, remaining flags.

## Provider layer

`backend/engine/llm/`. `LLMProvider.rewrite(system, user, params) -> str`. One OpenAI-compatible class (Groq, OpenRouter, Cerebras, Mistral, Together) plus Gemini. Keys from env or Settings, server-side `data/.env`, never hard-coded/logged. Editable prompts in `backend/engine/llm/prompts/*.md`. Offline fallback toggle.

## Learning tables (no voice feature)

`example_pairs(tone, strength, operation, source_text, rewritten_text, score_before, score_after, rating)`, `feedback`, `llm_cache`. Top-rated pairs for same tone/operation are injected as few-shot; accepted/edited rewrites become examples. Seed set included. No `style_profiles`, no "match my voice".

## Voice removal

Voice/style-profile functionality was removed cleanly for now and can be re-added later; restore from `pre-voice-removal`. The grammatical `active/passive voice` catalog sections are unrelated writing-pattern references, not a voice feature, and were kept.

## Offline engine

`backend/engine/` keeps `clean`, `blocks`, `sentences`, `protect`, `plan`, `rules`, `ranker`, `validators`, `skill.scan`, `apply_skill`, `assemble`. Offline fallback uses the same validators and never changes meaning silently.

## Privacy

Only the sentences being rewritten are sent, each in its own provider call, plus read-only adjacent context, a few local examples, and the banned-phrase list; never the whole write-up. Documents, references, keys and feedback stay local in `data/`. With no key or offline fallback, nothing is sent. Results are a writing aid and do not guarantee any outcome on third-party detectors.

## Tests

`pytest` offline by default with `PHRASIA_DATA_DIR`; mocked providers; no real keys. `npm run typecheck`, `npm run build`. See `docs/NOTES.md`, `docs/THIRD_PARTY.md`.
