"""Step 3: usage table, retry-failed-chunks, SSRF guard."""
from __future__ import annotations

import pytest

from backend.api.errors import UnsafeEndpoint, validate_base_url
from backend.db import repository


def test_usage_table_round_trip() -> None:
    repository.record_usage("gemini", "gemini-2.5-flash", "humanize_chunk", 123, 456)
    rows = repository.list_usage(limit=10)
    assert rows
    row = rows[0]
    assert row["provider_id"] == "gemini"
    assert row["operation"] == "humanize_chunk"
    assert row["input_chars"] == 123
    assert row["output_chars"] == 456
    assert row["created_at"]


def test_retry_failed_chunks_resets_only_errors() -> None:
    job_id = repository.create_job(
        document_id=repository.create_document("J"),
        source_version_id=repository.add_version(repository.create_document("J2"), "source", "t"),
        status="failed",
        mode="balanced",
        intensity="medium",
        options_json="{}",
        total_chunks=3,
    )
    repository.create_chunks(job_id, [{"text": f"chunk {i}", "separator": ""} for i in range(3)])
    chunks = repository.list_chunks(job_id)
    assert len(chunks) == 3

    repository.update_chunk(int(chunks[0]["id"]), status="completed", output_text="ok")
    repository.update_chunk(int(chunks[1]["id"]), status="error", error="boom", attempt_count=2)
    repository.update_chunk(int(chunks[2]["id"]), status="pending")

    reset = repository.retry_failed_chunks(job_id)
    assert reset == 1
    chunks = repository.list_chunks(job_id)
    by_seq = {c["seq"]: c for c in chunks}
    assert by_seq[0]["status"] == "completed"  # untouched
    assert by_seq[1]["status"] == "pending"
    assert by_seq[1]["error"] is None
    assert by_seq[2]["status"] == "pending"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/v1",
        "http://localhost:8000/v1",
        "http://[::1]:8000/v1",
        "http://10.0.0.1/v1",
        "http://192.168.1.10/v1",
        "http://169.254.1.1/v1",
        "http://100.64.0.1/v1",
    ],
)
def test_ssrf_guard_blocks_private_and_loopback(url: str) -> None:
    with pytest.raises(UnsafeEndpoint):
        validate_base_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com/v1",
        "https://generativelanguage.googleapis.com/v1beta",
    ],
)
def test_ssrf_guard_accepts_public_urls(url: str) -> None:
    assert validate_base_url(url).startswith("http")
    assert not validate_base_url(url).endswith("/")


def test_ssrf_guard_rejects_non_http() -> None:
    with pytest.raises(UnsafeEndpoint):
        validate_base_url("ftp://example.com")


def test_ssrf_guard_rejects_empty() -> None:
    assert validate_base_url("") == ""
