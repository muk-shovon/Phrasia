"""HTTP API tests against the real app."""
from __future__ import annotations


def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_removed_routes_are_gone(client) -> None:
    assert client.get("/api/meta").status_code == 404
    assert client.post("/api/diff", json={"original": "a", "rewritten": "b"}).status_code in {404, 405}
    assert client.get("/api/jobs").status_code == 404
    assert client.get("/api/settings").status_code == 404


def test_humanize_response_shape(client) -> None:
    response = client.post(
        "/api/humanize",
        json={
            "text": "Through digital tools, employees can share updates with their teams.",
            "tone": "casual",
            "strength": "medium",
            "variation": 0,
            "clean_invisible": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"rewritten", "sentences", "diff", "style_check", "document_id"}
    assert body["rewritten"]
    assert body["sentences"]
    assert "segments" in body["diff"]
    check = body["style_check"]
    assert set(check) == {
        "patterns_before", "patterns_after", "patterns_removed",
        "sentences_restructured", "sentences_total", "words_changed_pct",
    }
    assert check["sentences_total"] == 1


def test_humanize_validation(client) -> None:
    assert client.post("/api/humanize", json={"text": ""}).status_code == 422
    assert client.post("/api/humanize", json={"text": "   "}).status_code == 422
    assert client.post("/api/humanize", json={"text": "Hello.", "variation": -1}).status_code == 422


def test_export_is_plain_utf8_and_docx(client) -> None:
    txt = client.post("/api/export", json={"text": "Cafe naive resume", "title": "Cafe"})
    assert txt.status_code == 200
    assert txt.content.decode("utf-8") == "Cafe naive resume"
    assert "attachment" in txt.headers["content-disposition"]

    docx = client.post("/api/export/docx", json={"text": "Hello world.", "title": "Hello"})
    assert docx.status_code == 200
    assert docx.content[:2] == b"PK"


def test_reference_library_and_plagiarism(client) -> None:
    reference = (
        "Remote work changed how teams communicate. Managers traded hallway chats "
        "for written updates, which exposed missing context. The best teams wrote "
        "more, not less, and made decisions visible to everyone who was not in the room."
    )
    created = client.post("/api/plagiarism/references", json={"title": "Earlier essay", "text": reference})
    assert created.status_code == 201
    reference_id = created.json()["id"]
    assert client.get("/api/plagiarism/references").json()["references"][0]["title"] == "Earlier essay"

    report = client.post("/api/plagiarism/check", json={"text": reference}).json()
    assert report["local_only"] is True
    assert report["coverage_percent"] >= 50
    assert report["matches"]
    assert "web" not in report

    assert client.delete(f"/api/plagiarism/references/{reference_id}").status_code == 200
    assert client.delete(f"/api/plagiarism/references/{reference_id}").status_code == 404


def test_detector_is_a_pattern_signal(client) -> None:
    response = client.post("/api/detector/check", json={"text": "Furthermore, this is a great question."})
    assert response.status_code == 200
    body = response.json()
    assert "not proof of authorship" in body["disclaimer"].lower()
    assert isinstance(body["patterns"], list)
    assert "%" not in str(body)


def test_unknown_api_path_is_404(client) -> None:
    assert client.get("/api/does-not-exist").status_code == 404
