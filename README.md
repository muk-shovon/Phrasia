<div align="center">

# Phrasia

### Clearer, more considered writing, with the style of a person.

An online-first writing workspace for humanizing text with a hosted language model, checking it against your own references, spotting common writing patterns, and keeping a local history of your work. When no hosted provider is available, a built-in rule engine takes over.

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/TypeScript-Frontend-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript frontend" />
  <img src="https://img.shields.io/badge/Storage-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite storage" />
  <img src="https://img.shields.io/badge/License-MIT-6A994E?style=for-the-badge" alt="MIT License" />
</p>

<p>
  <a href="#-features">Features</a> ·
  <a href="#-quick-start">Quick start</a> ·
  <a href="#-how-it-works">How it works</a> ·
  <a href="#-developer-setup">Development</a> ·
  <a href="#-faq">FAQ</a>
</p>

</div>

---

## What is Phrasia?

Phrasia is a **writing workspace** with several tools. Its rewriting step uses a hosted language model for natural, human-sounding prose, then runs a local rule engine as a safety pass and as an offline fallback. You bring your own provider key (Groq, Cerebras, Gemini, Mistral, OpenRouter, or Together), or you run entirely on the local engine.

The web interface is written in TypeScript and is included as a prebuilt bundle, so you do not need Node.js to run the application.

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>✍️ Humanizer</h3>
      Rewrite text with a hosted model. Choose tone, intensity, and provider, watch each pass, review changed wording and meaning-risk markers, and re-humanize only the passages that still need work.
    </td>
    <td width="50%">
      <h3>🔎 Plagiarism</h3>
      Compare text with reference documents in your own local library. Similarity results are limited to the references you have added.
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>📊 Style Signal</h3>
      Highlight common writing patterns from the local pattern catalog. It is a writing aid, not an authorship detector.
    </td>
    <td width="50%">
      <h3>🗂️ History</h3>
      Keep source and rewritten versions on your computer. Review or remove locally stored documents and versions.
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⚙️ Settings</h3>
      Add a provider key, pick a default model, test the connection, and set the offline fallback.
    </td>
    <td width="50%">
      <h3>🧠 Local fallback</h3>
      If every hosted provider fails, the deterministic rule engine finishes the rewrite. Nothing is lost when the network is down.
    </td>
  </tr>
</table>

### How your text is handled

- **Online-first rewriting** — a hosted model does the style work, so the output reads like natural writing rather than a set of rule substitutions.
- **Local safety pass** — numbers, names, URLs, quotations, and negations are protected before the model is called and re-checked afterwards. Unsafe drafts are rejected and the original sentence is kept.
- **Only the rewritten text leaves your machine** — the passage is sent to the provider you choose, with a short style guide. Your documents, reference library, history, and keys stay local.
- **Keys are stored locally** — a saved key lives in `data/.env` on your computer and is never returned by the API. Environment variables take precedence if you set them.
- **Offline fallback** — with no key, no network, or every provider failing, Phrasia uses its rule engine and says so in the result.
- **No web-wide plagiarism search** — comparisons use only your own reference library.

> **A note on results:** Phrasia is a style-improvement tool, not a guarantee about any AI-writing or plagiarism detector. Results are a writing aid.

## 🚀 Quick start

### Requirements

- Python **3.11, 3.12, or 3.13** — [Download Python](https://www.python.org/downloads/)
- Internet access for the first Python dependency installation only
- Internet access for hosted rewriting, plus a provider key (optional; the local engine works without either)
- Node.js **20 or newer** only if you are developing the frontend

**Windows:** During Python installation, enable **Add python.exe to PATH**.

### 1. Get the project

Clone the repository:

```bash
git clone https://github.com/muk-shovon/Phrasia.git
cd Phrasia
```

Or download the repository ZIP and extract it.

### 2. Start Phrasia

```bash
python run.py
```

On Windows, you can also use:

```powershell
py -3 run.py
```

That is all. On the first run, the launcher creates a `.venv` environment and installs the required Python dependencies. It then opens Phrasia at:

**http://127.0.0.1:8000**

Later runs reuse the existing environment. If port `8000` is already occupied, Phrasia checks the next available ports through `8010`.

## ⚙️ Manual setup

Use these steps if you prefer to manage the virtual environment yourself.

<details>
<summary><strong>Windows PowerShell</strong></summary>

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --default-timeout=100 -r requirements.txt
python run.py
```

If script activation is blocked for the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

</details>

<details>
<summary><strong>Windows Command Prompt</strong></summary>

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --default-timeout=100 -r requirements.txt
python run.py
```

</details>

<details>
<summary><strong>macOS or Linux</strong></summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --default-timeout=100 -r requirements.txt
python run.py
```

</details>

## 🔑 Connect a hosted provider (optional)

Phrasia works without a provider, but hosted rewriting gives the most natural results.

1. Open **Settings** in the app.
2. Pick a provider — Groq, Cerebras, Gemini, Mistral, OpenRouter, or Together. Each one offers a free tier; the Settings page links to its key page.
3. Paste the key and choose a model. **Test key** checks the connection.
4. Turn on **Use hosted rewriting** and keep **Offline fallback** on.

Keys are written to `data/.env` on your machine and are never returned by the API. You can also set an environment variable such as `GROQ_API_KEY` before starting Phrasia; environment variables take precedence over a saved file.

If you prefer to run only the local engine, leave the key fields empty or switch hosted rewriting off. The Humanizer will use the rule engine and label the result accordingly.

## 🧭 Explore the workspace

| Tool | What it does |
|---|---|
| **Humanizer** | Paste text, select a tone and intensity, and choose a provider. Review the rewrite, changed wording, meaning-risk markers, pattern counts, and passages that still need attention. Re-humanize a single passage without rerunning the whole document. Controls include prose dashes, straight quotation marks, and invisible-character cleanup. |
| **Settings** | Save a provider key, choose a default model, test the connection, and set the offline fallback. |
| **Plagiarism** | Add reference documents to your local library and compare text against those references. Phrasia does not search the web. |
| **Style Signal** | Inspect matches from the same local pattern catalog used by the Humanizer. Results do not establish who wrote a document. |
| **History** | Open or remove locally stored documents and versions. History is backed by the SQLite database in `data/`. |

## 🧠 How it works

The Humanizer is **online-first with offline fallback**, with a local rule engine as pre/post-processing, validator and fallback. The whole write-up is never sent in one request.

1. Cleans the input and splits it into paragraphs, then sentences, preserving boundaries.
2. Extracts protected spans (numbers, names, URLs, emails, code, citations, quoted lines) and swaps them for placeholders.
3. Analyzes per sentence: length, opening, pattern hits; and per text: sentence-length variance (burstiness), repeated openers, hedge/quantifier density, pronoun mix.
4. Plans one operation per sentence, only: word/phrase swap, clause reorder, split, merge adjacent pair, new opening, shorter punchy rewrite, or nearly unchanged. No active↔passive voice changes. Natural short/medium/long mix.
5. Rewrites **one sentence or adjacent pair per provider call** with operation, previous/next sentence read-only context, tone/strength, a few retrieved example pairs for the same tone/operation, and the banned phrase list. Limited concurrency (~4), retries, provider fallback, cache keyed by `(sentence, operation, tone, strength)`. Output only the rewritten sentence.
6. Restores protected spans and validates: facts, negations, placeholders, grammar, length; plus a cheap second meaning check. On failure retry once with a stricter prompt, then keep the original sentence.
7. Rescans the whole text. Only still-flagged sentences are re-humanized, up to N rounds (`light=1`, `medium=2`, `heavy=3`, `ninja=4`), stopping early at target.
8. Runs the local rule engine as a final safety and cleanup pass, restores spans, and returns a per-sentence report: original, final, operation, validator result, remaining flags.

Provider calls have a timeout and retry with backoff. On `429`/`5xx`/timeout the chain moves to the next ready provider; if all fail, the local engine finishes and says so. Accepted and edited rewrites are saved locally as example pairs. Results are cached locally.

### Without a key

With no provider key, hosted rewriting disabled, or the fallback on and every provider failing, the deterministic rule engine runs the whole rewrite. It applies safe pattern edits, leaves context-dependent cases unchanged, and marks them for review. This is the same engine that has always shipped with Phrasia.

## 🛠️ Launcher options

You can pass these options when starting the application:

```bash
python run.py --no-browser
python run.py --host 0.0.0.0
python run.py --no-bootstrap
```

| Option | Description |
|---|---|
| `--no-browser` | Start the server without automatically opening a browser. |
| `--host ADDRESS` | Change the bind address from the private default, `127.0.0.1`. |
| `--no-bootstrap` | Disable automatic virtual-environment creation and dependency installation. |

The default host keeps the application private to the local machine. Only expose it on a network you trust.

## 💾 Local data and backups

Phrasia automatically creates its local database at:

```text
data/phrasia.db
```

A saved provider key is stored in `data/.env`. The `data/` directory is excluded from Git.

- **Back up:** Close Phrasia and copy the entire `data/` folder.
- **Restore:** Close Phrasia and replace `data/` with your backup.
- **Reset:** Close Phrasia and delete `data/`. The next start creates a new database.

## 🔄 Updating

If you installed Phrasia with Git:

```bash
git pull
python run.py
```

The launcher installs dependency updates when packages are missing. To apply changed version ranges immediately, activate `.venv` and run the installation command from the manual setup section.

## 🧑‍💻 Developer setup

### Backend environment

```bash
python -m venv .venv
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Frontend dependencies

```bash
cd frontend
npm ci
```

### Run the development servers

Use two terminals.

**Terminal 1 — Python backend:**

```bash
python run.py --no-browser
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

### Run checks

```bash
python -m pytest
cd frontend
npm run typecheck
npm run build
```

`frontend/dist/` is committed deliberately so users can run Phrasia without Node.js. Maintainers should rebuild and commit this directory before a release whenever the frontend changes.

## 📁 Project structure

```text
Phrasia/
├── backend/                 Python API, SQLite repository, and writing engine
│   ├── engine/llm/          Hosted providers, prompts, retrieval, rewrite passes
│   └── engine/data/         Versioned rule and language data
├── data/                    Local runtime database and saved keys; not committed
├── docs/                    Reference and third-party documentation
├── frontend/
│   ├── src/                 TypeScript, HTML, and CSS sources
│   └── dist/                Committed browser bundle
├── tests/                   Python tests and fixtures
├── run.py                   Cross-platform launcher and first-run setup
├── requirements.txt         Runtime Python dependencies
└── requirements-dev.txt     Test-only Python dependencies
```

## 🧰 Troubleshooting

| Problem | What to do |
|---|---|
| `python` is not found | Install Python 3.11–3.13 from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH**. On macOS/Linux, try `python3 run.py`. |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again. Automatic setup does not require activation. |
| Pip is slow or reports a network error | Retry with `python -m pip install --default-timeout=100 -r requirements.txt`. |
| Wrong Python version | Run `python --version` and install Python 3.11, 3.12, or 3.13. |
| `venv` is unavailable on Debian/Ubuntu | Run `sudo apt install python3-venv`, then start Phrasia again. |
| `externally-managed-environment` | Do not install into the system Python. Use `python run.py` or activate `.venv` first. |
| Port 8000 is in use | Phrasia checks ports 8001 through 8010. Close the other service if all are occupied. |
| Blank page or missing `dist` | Use a complete release or clone. Developers can run `cd frontend`, `npm ci`, and `npm run build`. |
| Windows console text looks garbled | Use Windows Terminal, or run `chcp 65001` before starting. The launcher also configures UTF-8 output. |
| The folder is not writable | Move Phrasia to Documents, Downloads, or another user-owned folder instead of Program Files. |
| Database is locked or corrupt | Close every Phrasia process, back up `data/`, then rename or remove `data/phrasia.db` and restart. |
| Hosted rewriting is not used | Open **Settings**, confirm a key is saved and **Use hosted rewriting** is on, then press **Test key**. |
| A provider returns `429` or `5xx` | The chain tries the next ready provider. Add a second key or keep the offline fallback on. |
| The result says the local engine was used | No provider answered. Check the key, the model name, and your connection. |

## ❔ FAQ

<details>
<summary><strong>Does Phrasia send my text anywhere?</strong></summary>

Only the sentences being rewritten are sent, and only to the hosted provider you choose, when hosted rewriting is on. Each provider call contains one sentence or adjacent pair plus read-only previous/next context, tone/strength, a few local example pairs, and the banned-phrase list; never the whole write-up. Nothing else leaves your machine: documents, references, feedback, and keys stay in the local `data/` folder. With no key or with the offline fallback, nothing is sent at all.

</details>

<details>
<summary><strong>Does it need an API key?</strong></summary>

Only for hosted rewriting. Add a key from a supported provider on the Settings page; it is stored locally in `data/.env`. Without a key, Phrasia runs entirely on its local rule engine.

</details>

<details>
<summary><strong>What happens if the provider is down or rate-limited?</strong></summary>

The request moves to the next ready provider with a key. If every provider fails, the local rule engine finishes the rewrite and the result shows that the fallback was used.

</details>

<details>
<summary><strong>Does a low plagiarism result cover the internet?</strong></summary>

No. It covers only the references in your local library. Phrasia does not perform a web-wide search.

</details>

<details>
<summary><strong>Can I use it without Node.js?</strong></summary>

Yes. The committed frontend bundle is served by Python. Node.js 20 or newer is needed only when changing the frontend.

</details>

<details>
<summary><strong>Can I bind it to another interface?</strong></summary>

Yes. Use `--host ADDRESS`. The default is private to the local machine; only expose it on a network you trust.

</details>

## 📚 Project documentation

- [Project plan](PLAN.md)
- [Audit](AUDIT.md)
- [Decisions](DECISIONS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Historical notes](docs/NOTES.md)
- [Third-party notices](docs/THIRD_PARTY.md)

## 📄 License

Phrasia is available under the [MIT License](LICENSE).

---

<div align="center">

**Phrasia** · Online-first writing tools, local fallback.

<sub>Only the text you rewrite is sent.</sub>

</div>
