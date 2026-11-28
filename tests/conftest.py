"""Test bootstrap: isolate every run from the real data directory."""
from __future__ import annotations

import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="phrasia-tests-")
os.environ["PHRASIA_DATA_DIR"] = _TEST_DIR
os.environ["PHRASIA_DB_PATH"] = os.path.join(_TEST_DIR, "test.db")
for _key in (
    "GROQ_API_KEY", "CEREBRAS_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "MISTRAL_API_KEY", "OPENROUTER_API_KEY", "TOGETHER_API_KEY",
):
    os.environ.pop(_key, None)

import pytest  # noqa: E402

from backend.config import DATA_DIR  # noqa: E402
from backend.db import repository  # noqa: E402


@pytest.fixture(autouse=True)
def clean_local_config():
    for name in ("settings.json", ".env"):
        path = DATA_DIR / name
        try:
            path.unlink()
        except OSError:
            pass
    yield


@pytest.fixture(autouse=True)
def clean_db():
    repository.init_db()
    repository.reset_db_for_tests()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client
