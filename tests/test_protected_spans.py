"""Protected spans: mask before the LLM, restore after, retry on mismatch."""
from __future__ import annotations

from backend.core import protected_spans


def test_url_and_email_are_extracted() -> None:
    text = "Visit https://example.com or mail me at me@example.com please."
    redacted, spans = protected_spans.extract_spans(text)
    assert redacted.count("[PHRASIA_SPAN_") == 2
    assert "https://example.com" not in redacted
    assert "me@example.com" not in redacted
    assert len(spans) == 2


def test_code_fence_and_inline_code_are_protected() -> None:
    text = "Run `pip install` then\n\n```bash\npython -m backend.main\n```"
    redacted, spans = protected_spans.extract_spans(text)
    assert "`pip install`" not in redacted
    assert "python -m backend.main" not in redacted
    assert len(spans) == 2


def test_restore_is_exact() -> None:
    text = "See https://example.com/a?b=1 and `code here` done."
    redacted, spans = protected_spans.extract_spans(text)
    restored = protected_spans.restore_spans(redacted, spans)
    assert restored == text.strip()


def test_restore_fails_when_a_placeholder_is_missing() -> None:
    text = "Read https://example.com now."
    redacted, spans = protected_spans.extract_spans(text)
    bad = redacted.replace(spans[0].placeholder, "")
    assert protected_spans.restore_spans(bad, spans) is None


def test_restore_fails_on_duplicates() -> None:
    text = "Read https://example.com now."
    redacted, spans = protected_spans.extract_spans(text)
    duplicated = redacted + "\n" + redacted
    assert protected_spans.restore_spans(duplicated, spans) is None


def test_no_spans_returns_text_unchanged() -> None:
    text = "Plain text without anything special."
    redacted, spans = protected_spans.extract_spans(text)
    assert spans == []
    assert protected_spans.restore_spans(redacted, spans) == text.strip()
