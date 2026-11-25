# Phrasia

Phrasia is a private, offline writing workspace with four local tools:

- **Humanizer** — deterministic sentence rewriting and review hints.
- **Plagiarism** — similarity checks against references you add to your own library.
- **Style Signal** — highlights common writing patterns without making an authorship claim.
- **History** — stores source and rewritten versions on this computer.

All writing logic runs in a rule-based Python engine. Phrasia uses no AI service, needs no API key, and makes no external network request after the first dependency install. The web interface is written in TypeScript and is included prebuilt.

## Requirements

- Python 3.11, 3.12, or 3.13 from [python.org](https://www.python.org/downloads/).
- Internet access for the first Python dependency install only.
- Node.js 20 or newer only if you are changing the frontend.

On Windows, enable **Add python.exe to PATH** in the Python installer.

## Quick start

Download the repository ZIP and extract it, or clone it:

```text
git clone https://github.com/muk-shovon/Phrasia.git
cd Phrasia
```

Run one command:

```text
python run.py
```

On Windows, this form also works:

```text
py -3 run.py
```

The first run creates `.venv`, installs the Python dependencies, and then opens the app at <http://127.0.0.1:8000>. Later runs reuse that environment. If port 8000 is busy, Phrasia tries the next port through 8010.

## Manual setup

Use this route if you prefer to manage the virtual environment yourself.

### Windows PowerShell

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

### Windows Command Prompt

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --default-timeout=100 -r requirements.txt
python run.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --default-timeout=100 -r requirements.txt
python run.py
```

## Page guide

### Humanizer

Paste text, choose a tone and strength, and run the rewrite. The result shows changed wording, meaning-risk markers, pattern counts, and passages that still need review. Controls cover prose dashes, straight quotation marks, and invisible-character cleanup. Text and DOCX export stay local.

### Plagiarism

Add reference documents to the local library, then compare text against them. Results measure overlap only with that library; Phrasia does not search the web.

### Style Signal

Inspect pattern matches from the same local catalog used by the Humanizer. This is a writing aid, not proof of who wrote a document.

### History

Open or remove locally stored documents and versions. History is backed by the SQLite file in `data/`.

## Launcher options

```text
python run.py --no-browser
python run.py --host 0.0.0.0
python run.py --no-bootstrap
```

- `--no-browser` starts the server without opening a browser.
- `--host ADDRESS` changes the bind address from the private default `127.0.0.1`.
- `--no-bootstrap` disables automatic virtual-environment creation and dependency installation.

## Local data and backups

Phrasia creates `data/phrasia.db` automatically. The `data/` directory is excluded from Git.

- **Back up:** close Phrasia and copy the entire `data/` folder.
- **Restore:** close Phrasia and replace `data/` with the backup.
- **Reset:** close Phrasia and delete `data/`; the next start creates a new database.

## Updating

From a Git clone:

```text
git pull
python run.py
```

The launcher installs dependency updates when packages are missing. To apply changed version ranges immediately, activate `.venv` and run the install command from the manual setup section.

## Troubleshooting

| Problem | What to do |
|---|---|
| `python` is not found | Install Python 3.11-3.13 from python.org and enable **Add python.exe to PATH**. On macOS/Linux, try `python3 run.py`. |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again. Automatic setup does not require activation. |
| Pip is slow or reports a network error | Retry with `python -m pip install --default-timeout=100 -r requirements.txt`. |
| Wrong Python version | Run `python --version` and install Python 3.11, 3.12, or 3.13. |
| `venv` is unavailable on Debian/Ubuntu | Run `sudo apt install python3-venv`, then start Phrasia again. |
| `externally-managed-environment` | Do not install into the system Python. Use `python run.py` or activate `.venv` first. |
| Port 8000 is in use | Phrasia automatically checks ports 8001 through 8010. Close the other service if all are occupied. |
| Blank page or missing `dist` | Use a complete release or clone. Developers can run `cd frontend`, `npm ci`, and `npm run build`. |
| Windows console text looks garbled | Use Windows Terminal, or run `chcp 65001` before starting. The launcher also configures UTF-8 output. |
| The folder is not writable | Move Phrasia to Documents, Downloads, or another user-owned folder instead of Program Files. |
| Database is locked or corrupt | Close every Phrasia process, back up `data/`, then rename or remove `data/phrasia.db` and restart. |

## Developer setup

Install Python development dependencies:

```text
python -m venv .venv
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Install the frontend dependencies:

```text
cd frontend
npm ci
```

For frontend development, use two terminals:

```text
python run.py --no-browser
```

```text
cd frontend
npm run dev
```

Developer checks:

```text
python -m pytest
cd frontend
npm run typecheck
npm run build
```

`frontend/dist/` is committed deliberately so users do not need Node.js. Maintainers should rebuild and commit it before a release whenever the frontend changes.

## Project structure

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

## How the writing pass works

Phrasia cleans and protects the input, scans one versioned pattern catalog, applies safe automatic edits, ranks conservative structural candidates, validates retained facts, and scans the final text again.

Automatic edits cover prose dashes, chat residue, stock closers, decorative bold, selected overused words, and similar patterns. Vague claims, unsupported authority, source-limit language, and other context-dependent cases are left unchanged and marked for review.

The engine intentionally leaves a sentence alone when no safe rule exists. It is less fluent than a language model, and it is a style-improvement tool with no guarantee about any detector.

## FAQ

**Does Phrasia send my text anywhere?**
No. Rewriting, reference comparison, style scanning, and storage run on your computer.

**Does it need an API key?**
No.

**Does a low plagiarism result cover the internet?**
No. It covers only references in your local library.

**Can I use it without Node.js?**
Yes. The committed frontend bundle is served by Python.

**Can I bind it to another interface?**
Yes, with `--host`. The default is private to the local machine; only expose it on a network you trust.

## Project docs

- [Plan](PLAN.md)
- [Audit](AUDIT.md)
- [Decisions](DECISIONS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Historical notes](docs/NOTES.md)
- [Third-party notices](docs/THIRD_PARTY.md)

Phrasia is available under the [MIT License](LICENSE).
