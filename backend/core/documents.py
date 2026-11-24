"""Text extraction and DOCX export (no local models, standard libraries + python-docx)."""
from __future__ import annotations

import io
from pathlib import Path

from backend.config import MAX_UPLOAD_BYTES

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".docx"}


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded TXT/Markdown/DOCX file."""
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValueError(f"The file is larger than the {limit_mb} MB limit.")

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".docx":
        return _extract_docx(data)
    if suffix in {".txt", ".md", ".markdown"}:
        return _decode(data)
    raise ValueError("Unsupported file type. Upload a .txt, .md or .docx file.")


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        if text.strip():
            return text.strip()
    raise ValueError("Could not read the file as text.")


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ValueError("DOCX support requires python-docx.") from exc

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise ValueError("This file is not a readable .docx document.") from exc

    blocks = [paragraph.text.strip() for paragraph in document.paragraphs]
    text = "\n\n".join(block for block in blocks if block)
    if not text.strip():
        raise ValueError("No text was found in that document.")
    return text


def export_docx(text: str) -> bytes:
    """Render plain text as a simple DOCX file with one paragraph per block."""
    from docx import Document
    from docx.shared import Pt

    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

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
