"""Repository lifecycle tests (SQLite only, no network)."""
from __future__ import annotations

from backend.db import repository


def test_document_version_job_chunk_lifecycle() -> None:
    document_id = repository.create_document("Draft", source_type="pasted")
    source_id = repository.add_version(document_id, "source", "Hello world. " * 20)
    job_id = repository.create_job(
        document_id=document_id,
        source_version_id=source_id,
        status="queued",
        mode="balanced",
        intensity="medium",
        options_json='{"preserve_formatting": true, "keep_quotes": true}',
        total_chunks=1,
        provider_id="gemini",
    )
    repository.create_chunks(job_id, [{"text": "Hello world.", "separator": ""}])

    assert repository.get_job(job_id)["status"] == "queued"
    assert len(repository.list_chunks(job_id)) == 1

    chunk = repository.list_chunks(job_id)[0]
    repository.update_chunk(
        int(chunk["id"]), status="completed", output_text="Hi world.", attempt_count=1
    )
    repository.update_job(job_id, status="completed", completed_chunks=1)

    detail = repository.get_job_detail(job_id)
    assert detail is not None
    assert detail["output_text"] is None  # no result version linked yet
    assert detail["chunks"][0]["status"] == "completed"

    result_id = repository.add_version(document_id, "humanized", "Hi world.")
    repository.update_job(job_id, result_version_id=result_id)

    detail = repository.get_job_detail(job_id)
    assert detail is not None
    assert detail["output_text"] == "Hi world."
    assert repository.list_documents()[0]["latest_job_status"] == "completed"


def test_deleting_a_document_removes_its_children() -> None:
    document_id = repository.create_document("Temp")
    version_id = repository.add_version(document_id, "source", "text")
    job_id = repository.create_job(
        document_id=document_id,
        source_version_id=version_id,
        status="queued",
        mode="balanced",
        intensity="medium",
        options_json="{}",
        total_chunks=1,
    )
    repository.create_chunks(job_id, [{"text": "text", "separator": ""}])

    assert repository.delete_document(document_id) is True
    assert repository.get_document(document_id) is None
    assert repository.get_job(job_id) is None
    assert repository.list_chunks(job_id) == []
    assert repository.delete_document(document_id) is False


def test_interrupted_jobs_become_paused() -> None:
    document_id = repository.create_document("Paused test")
    version_id = repository.add_version(document_id, "source", "hello")
    job_id = repository.create_job(
        document_id=document_id,
        source_version_id=version_id,
        status="running",
        mode="balanced",
        intensity="medium",
        options_json="{}",
        total_chunks=1,
    )
    assert repository.mark_interrupted_jobs_paused() >= 1
    assert repository.get_job(job_id)["status"] == "paused"


def test_provider_settings_round_trip() -> None:
    repository.upsert_provider_setting(
        "gemini", api_key="secret-value-1234", model="gemini-2.5-flash"
    )
    saved = repository.provider_setting("gemini")
    assert saved is not None
    assert saved["api_key"] == "secret-value-1234"

    repository.upsert_provider_setting("gemini", model="gemini-2.0-flash")
    assert repository.provider_setting("gemini")["api_key"] == "secret-value-1234"

    repository.delete_provider_key("gemini")
    assert repository.provider_setting("gemini")["api_key"] is None
