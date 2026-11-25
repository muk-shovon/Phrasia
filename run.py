"""Start the local Phrasia web app, bootstrapping Python dependencies if needed."""
from __future__ import annotations

import argparse
import importlib
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
DIST_INDEX = ROOT / "frontend" / "dist" / "index.html"
REQUIRED_MODULES = ("fastapi", "uvicorn", "pydantic", "docx")


def _configure_console() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


def _check_python() -> bool:
    version = sys.version_info
    if version < (3, 11):
        print("Phrasia requires Python 3.11, 3.12, or 3.13.")
        print("Install a supported version from https://www.python.org/downloads/.")
        return False
    if version >= (3, 14):
        print("Warning: Python 3.14+ is newer than the supported 3.11-3.13 range.")
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Phrasia locally.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1).")
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Do not create a virtual environment or install missing dependencies.",
    )
    return parser.parse_args()


def _imports_work() -> bool:
    try:
        for module in REQUIRED_MODULES:
            importlib.import_module(module)
    except (ImportError, OSError):
        return False
    return True


def _venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _manual_install_message(python) -> None:
    print("Try the install manually:")
    print(f'  "{python}" -m pip install --default-timeout=100 -r "{REQUIREMENTS}"')


def _install(python) -> bool:
    try:
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--default-timeout=100",
                "-r",
                str(REQUIREMENTS),
            ],
            cwd=ROOT,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        print("Dependency installation failed. Check your connection and folder permissions.")
        _manual_install_message(python)
        return False
    return True


def _create_venv() -> Optional[Path]:
    python = _venv_python()
    if python.is_file():
        return python
    try:
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], cwd=ROOT, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("Could not create .venv with Python's standard venv module.")
        if sys.platform.startswith("linux"):
            print("On Debian or Ubuntu, run: sudo apt install python3-venv")
        print(f'You can also create it manually with: "{sys.executable}" -m venv "{VENV}"')
        return None
    return python if python.is_file() else None


def _ensure_dependencies(no_bootstrap: bool) -> Optional[int]:
    if _imports_work():
        return None

    inside_venv = sys.prefix != sys.base_prefix
    bootstrapped = os.environ.get("PHRASIA_BOOTSTRAPPED") == "1"
    if inside_venv:
        print("Installing missing dependencies into the active virtual environment...")
        if not _install(sys.executable) or not _imports_work():
            return 1
        return None

    if no_bootstrap or bootstrapped:
        print("Required Python packages are missing and automatic setup is disabled.")
        _manual_install_message(sys.executable)
        return 1

    print("Creating .venv and installing dependencies, first run only...")
    python = _create_venv()
    if python is None or not _install(python):
        return 1

    environment = os.environ.copy()
    environment["PHRASIA_BOOTSTRAPPED"] = "1"
    completed = subprocess.run(
        [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
        cwd=ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def _free_port(host: str) -> Optional[int]:
    for port in range(8000, 8011):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind((host, port))
        except OSError:
            continue
        if port != 8000:
            print(f"Port 8000 is busy; using port {port}.")
        return port
    return None


def _open_browser_when_ready(host: str, port: int) -> None:
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{browser_host}:{port}/#/humanize"
    for _ in range(150):
        try:
            with socket.create_connection((browser_host, port), timeout=0.2):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.1)


def main() -> int:
    _configure_console()
    if not _check_python():
        return 1
    args = _parse_args()

    dependency_result = _ensure_dependencies(args.no_bootstrap)
    if dependency_result is not None:
        return dependency_result
    if not DIST_INDEX.is_file():
        print("frontend/dist is missing. Maintainers can rebuild it with: cd frontend && npm run build")
        return 1

    port = _free_port(args.host)
    if port is None:
        print("No free port was found from 8000 through 8010.")
        return 1

    import uvicorn

    no_browser = args.no_browser or os.environ.get("PHRASIA_DISABLE_BROWSER", "").lower() in {
        "1", "true", "yes",
    }
    if not no_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(args.host, port),
            daemon=True,
        ).start()

    print(f"Starting Phrasia on http://{args.host}:{port}")
    uvicorn.run("backend.main:app", host=args.host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
