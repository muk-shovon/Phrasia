"""Repository lifecycle tests (SQLite only)."""
from __future__ import annotations

from backend.db import repository


def test_document_version_lifecycle() -> None:
    document_id = repository.create_document("Draft", source_type="pasted")
    source_id = repository.add_version(document_id, "source", "Hello world. " * 20)
    result_id = repository.add_version(document_id, "humanized", "Hi world.")

    assert repository.get_document(document_id)["title"] == "Draft"
    assert repository.get_version(source_id)["version_type"] == "source"
    assert repository.latest_version(document_id, "humanized") == "Hi world."
    assert len(repository.versions_with_content(document_id)) == 2
    assert repository.list_documents()[0]["version_count"] == 2
    assert result_id != source_id


def test_deleting_document_removes_versions() -> None:
    document_id = repository.create_document("Temp")
    version_id = repository.add_version(document_id, "source", "text")
    assert repository.delete_document(document_id) is True
    assert repository.get_document(document_id) is None
    assert repository.get_version(version_id) is None
    assert repository.delete_document(document_id) is False


def test_reference_library_round_trip() -> None:
    reference_id = repository.add_reference_document("Ref", "Some text here", 3)
    assert repository.list_reference_documents()[0]["title"] == "Ref"
    rows = repository.reference_documents_with_content()
    assert rows[0]["content"] == "Some text here"
    assert repository.delete_reference_document(reference_id) is True
    assert repository.delete_reference_document(reference_id) is False


def test_analysis_log_round_trip() -> None:
    repository.add_analysis("detector", "sample", "{}")
    rows = repository.list_analyses("detector")
    assert rows and rows[0]["input_excerpt"] == "sample"
