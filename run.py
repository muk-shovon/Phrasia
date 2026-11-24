"""Launch Phrasia on the local machine.

    python run.py

If frontend/dist is missing and Node/npm is available, run.py first runs
`npm install` + `npm run build` in frontend/. The server then binds to
127.0.0.1 and the browser opens. Set PHRASIA_PORT to change the port.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"
DISABLE_BROWSER = os.environ.get("PHRASIA_DISABLE_BROWSER", "").lower() in {
    "1",
    "true",
    "yes",
}


def _npm_available() -> bool:
    npm = shutil.which("npm")
    return bool(npm)


def _ensure_frontend_built() -> None:
    if DIST.is_dir() and (DIST / "index.html").is_file():
        return
    if not _npm_available():
        print(
            "frontend/dist is missing and npm was not found.\n"
            "Build the frontend yourself:\n  cd frontend && npm install && npm run build",
            flush=True,
        )
        return
    print("Building the frontend (npm install && npm run build)...", flush=True)
    subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund"],
        cwd=FRONTEND,
        check=False,
    )
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=False)
    if (DIST / "index.html").is_file():
        print(f"Frontend built to {DIST}", flush=True)
    else:
        print("Frontend build did not produce dist/index.html.", flush=True)


def main() -> None:
    _ensure_frontend_built()

    import uvicorn

    port = int(os.environ.get("PHRASIA_PORT", "8000"))
    if not DISABLE_BROWSER:
        import threading
        import webbrowser

        def open_browser() -> None:
            try:
                webbrowser.open(f"http://127.0.0.1:{port}/#/humanize")
            except Exception:
                pass

        threading.Thread(target=open_browser, daemon=True).start()

    print(f"Starting Phrasia on http://127.0.0.1:{port}", flush=True)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    sys.exit(main() or 0)
