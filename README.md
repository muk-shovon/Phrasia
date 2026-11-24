# Phrasia

Private local writing workspace: deterministic sentence rewriting, local plagiarism check against your own references, and a local style pattern signal. No network calls and no model.

## Windows setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000/. Dev mode: run `npm run dev` in `frontend/` and `python run.py` in the repo root.

## What works

- Humanizer: tone, strength, variation, invisible-character cleanup, per-sentence diff and highlight, txt/docx export.
- Local plagiarism check with reference library (shingles, Jaccard, difflib).
- Detector style signal from our own pattern list, with no verdict or score.
- History of documents and versions in local SQLite.

## Not implemented

No LLM, API keys, hosted endpoints, detector evasion, watermark removal, automatic citations, web search, accounts or cloud sync.

## Limits

Rule-based and less fluent than a language model. Sentences stay unchanged when no safe rule exists. No claim is made about any detector.
