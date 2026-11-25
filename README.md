<div align="center">

# Phrasia

### Your private workspace for clearer, more considered writing.

A local-first writing toolkit for humanizing text, checking it against your own references, spotting common writing patterns, and keeping a local history of your work.

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

Phrasia is a **private, offline writing workspace** with four local tools. Its writing logic runs in a rule-based Python engine: it does not use an AI service, does not require an API key, and makes no external network requests after the initial dependency installation.

The web interface is written in TypeScript and is included as a prebuilt bundle, so you do not need Node.js to run the application.

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>✍️ Humanizer</h3>
      Rewrite sentences with adjustable tone and strength. Review changed wording, meaning-risk markers, pattern counts, and passages that may need another look.
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
</table>

### Built around local use

- **No AI service** — rewriting is handled by a deterministic, rule-based Python engine.
- **No API key** — no external AI credentials are needed.
- **Local storage** — document history is stored in SQLite on your computer.
- **Local exports** — text and DOCX export stay local.
- **No web-wide plagiarism search** — comparisons use only your own reference library.

> **A note on results:** Phrasia is a style-improvement tool, not a guarantee about any AI-writing or plagiarism detector. It intentionally leaves sentences unchanged when it cannot apply a safe rule.

## 🚀 Quick start

### Requirements

- Python **3.11, 3.12, or 3.13** — [Download Python](https://www.python.org/downloads/)
- Internet access for the first Python dependency installation only
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

## 🧭 Explore the workspace

| Tool | What it does |
|---|---|
| **Humanizer** | Paste text, select a tone and strength, and review the rewrite, changed wording, meaning-risk markers, pattern counts, and passages that still need attention. Controls include prose dashes, straight quotation marks, and invisible-character cleanup. |
| **Plagiarism** | Add reference documents to your local library and compare text against those references. Phrasia does not search the web. |
| **Style Signal** | Inspect matches from the same local pattern catalog used by the Humanizer. Results do not establish who wrote a document. |
| **History** | Open or remove locally stored documents and versions. History is backed by the SQLite database in `data/`. |

## 🧠 How it works

Phrasia uses a rule-based writing pass rather than a hosted language model.

1. Cleans and protects the input.
2. Scans a versioned pattern catalog.
3. Applies safe automatic edits.
4. Ranks conservative structural candidates.
5. Validates retained facts.
6. Scans the final text again.

Automatic edits cover prose dashes, chat residue, stock closers, decorative bold, selected overused words, and similar patterns. Context-dependent cases — such as vague claims, unsupported authority, and source-limit language — are left unchanged and marked for review.

The engine deliberately avoids rewriting a sentence when no safe rule applies. This makes its output less fluent than a language model in some cases, but keeps the process deterministic and reviewable.

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

The `data/` directory is excluded from Git.

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
│   └── engine/data/         Versioned rule and language data
├── data/                    Local runtime database; not committed
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

## ❔ FAQ

<details>
<summary><strong>Does Phrasia send my text anywhere?</strong></summary>

No. Rewriting, reference comparison, style scanning, and storage run on your computer.

</details>

<details>
<summary><strong>Does it need an API key?</strong></summary>

No. Phrasia does not use an external AI service.

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

**Phrasia** · Private writing tools, running locally.

<sub>Built for thoughtful writing and human review.</sub>

</div>
