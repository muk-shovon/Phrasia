"""Launch Phrasia on the local machine.

    python run.py

The server binds to 127.0.0.1 only. Set PHRASIA_PORT to change the port.
"""
from __future__ import annotations

import os

import uvicorn

from backend.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PHRASIA_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port)
