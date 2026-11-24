"""DOCX export helpers (standard library + python-docx)."""
from __future__ import annotations

import io
from pathlib import Path


def export_docx(text: str) -> bytes:
    """Render plain text as a simple DOCX file with one paragraph per block."""
    from docx import Document

    document = Document()
    for block in text.split("\n\n"):
        cleaned = block.strip("\n")
        if cleaned.strip():
            document.add_paragraph(cleaned.strip())

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def safe_filename(title: str, extension: str) -> str:
    base = "".join(
        char for char in (title or "phrasia").strip() if char.isalnum() or char in " -_"
    ).strip()
    base = (base or "phrasia")[:80].replace(" ", "-")
    return f"{base}.{extension}"
