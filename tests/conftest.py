"""Test bootstrap: isolate every run from the real data directory."""
from __future__ import annotations

import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="phrasia-tests-")
os.environ["PHRASIA_DATA_DIR"] = _TEST_DIR
os.environ["PHRASIA_DB_PATH"] = os.path.join(_TEST_DIR, "test.db")
os.environ["PHRASIA_CHUNK_CHARS"] = "2560"

import pytest  # noqa: E402

from backend.db import repository  # noqa: E402


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
