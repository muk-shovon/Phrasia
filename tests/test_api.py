"""HTTP API tests against the real app (providers are faked)."""
from __future__ import annotations

from typing import Any

from backend.providers.registry import ProviderRegistry
from tests.test_humanizer import FakeProvider, _configured


def test_health_and_meta(client) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    meta = client.get("/api/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert body["modes"]
    assert body["intensities"]
    assert body["disclaimers"]["detector"].startswith("Local style signal")
    assert any(item["id"] == "pollinations" for item in body["providers"])
    assert any(item["id"] == "ovh" for item in body["providers"])


def test_humanize_validation(client) -> None:
    assert client.post("/api/humanize", json={"text": ""}).status_code == 422
    assert client.post("/api/humanize", json={"text": "   "}).status_code == 422


def test_humanize_round_trip(client, monkeypatch) -> None:
    fake = FakeProvider("A cleaner version of the text.")
    monkeypatch.setattr(
        ProviderRegistry, "configured", lambda self: [_configured("pollinations", fake)]
    )

    response = client.post(
        "/api/humanize",
        json={
            "text": "Original text that needs a calmer tone.",
            "title": "Test draft",
            "mode": "natural",
            "intensity": "light",
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job = client.get(f"/api/jobs/{job_id}")
    assert job.status_code == 200
    body = job.json()
    assert body["status"] == "completed"
    assert body["output_text"] == "A cleaner version of the text."
    assert body["progress_percent"] == 100

    export = client.get(f"/api/jobs/{job_id}/export?format=txt")
    assert export.status_code == 200
    assert export.content.decode("utf-8") == "A cleaner version of the text."
    assert "attachment" in export.headers["content-disposition"]

    docx_export = client.get(f"/api/jobs/{job_id}/export?format=docx")
    assert docx_export.status_code == 200
    assert docx_export.content[:2] == b"PK"

    documents = client.get("/api/documents").json()["documents"]
    assert documents[0]["title"] == "Test draft"
    assert documents[0]["latest_job_status"] == "completed"


def test_job_errors(client) -> None:
    assert client.get("/api/jobs/9999").status_code == 404
    assert client.post("/api/jobs/9999/retry").status_code == 404
    assert client.post("/api/jobs/9999/cancel").status_code == 404
    assert client.delete("/api/jobs/9999").status_code == 404
    assert client.get("/api/jobs/9999/export").status_code == 404


def test_settings_never_return_the_full_key(client) -> None:
    payload: dict[str, Any] = {
        "api_key": "sk-test-secret-9876",
        "model": "gpt-oss-20b",
    }
    saved = client.put("/api/settings/providers/pollinations", json=payload)
    assert saved.status_code == 200

    settings = client.get("/api/settings")
    assert settings.status_code == 200
    raw = settings.text
    assert "sk-test-secret-9876" not in raw
    card = next(
        item for item in settings.json()["providers"] if item["id"] == "pollinations"
    )
    assert card["masked_key"].endswith("9876")
    assert card["configured"] is True

    cleared = client.delete("/api/settings/providers/pollinations/key")
    assert cleared.status_code == 200


def test_enable_and_disable_provider(client) -> None:
    response = client.put(
        "/api/settings/providers/pollinations", json={"enabled": False}
    )
    assert response.status_code == 200
    card = next(
        item
        for item in client.get("/api/settings").json()["providers"]
        if item["id"] == "pollinations"
    )
    assert card["enabled"] == 0


def test_list_models_for_provider(client) -> None:
    response = client.post("/api/settings/providers/pollinations/models")
    assert response.status_code in {200, 404, 502}
    if response.status_code == 200:
        assert response.json()["models"]


def test_public_base_urls_are_accepted(client) -> None:
    response = client.put(
        "/api/settings/providers/pollinations", json={"base_url": "https://example.com/v1"}
    )
    assert response.status_code == 200
    assert response.json()["provider"]["base_url"].startswith("https://")


def test_private_base_urls_are_rejected(client) -> None:
    response = client.put(
        "/api/settings/providers/pollinations", json={"base_url": "http://127.0.0.1:8080/v1"}
    )
    assert response.status_code == 422
    assert "public online endpoint" in response.text


def test_preferences_validation(client) -> None:
    assert client.put("/api/settings/preferences", json={"preferred_provider": "nope"}).status_code == 422
    assert client.put("/api/settings/preferences", json={"preferred_provider": "ovh"}).status_code == 200


def test_reference_library_and_plagiarism(client) -> None:
    reference = (
        "Remote work changed how teams communicate. Managers traded hallway chats "
        "for written updates, which exposed missing context."
    )
    created = client.post("/api/plagiarism/references", json={"title": "Earlier essay", "text": reference})
    assert created.status_code == 201
    reference_id = created.json()["id"]

    listed = client.get("/api/plagiarism/references").json()["references"]
    assert listed[0]["title"] == "Earlier essay"

    report = client.post("/api/plagiarism/check", json={"text": reference}).json()
    assert report["local_only"] is True
    assert report["coverage_percent"] >= 50
    assert report["matches"]
    assert "web" in report
    assert "results" in report["web"]

    assert client.delete(f"/api/plagiarism/references/{reference_id}").status_code == 200
    assert client.delete(f"/api/plagiarism/references/{reference_id}").status_code == 404


def test_detector_endpoint(client) -> None:
    response = client.post(
        "/api/detector/check",
        json={"text": "Short, plain writing. It gets to the point. Nothing fancy here."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] in {"leans formulaic", "mixed", "leans conversational"}
    assert body["disclaimer"]


def test_unknown_api_path_is_404(client) -> None:
    assert client.get("/api/does-not-exist").status_code == 404
