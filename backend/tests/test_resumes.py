import io

import pytest

from app.core.errors import InvalidInputError
from app.services.resumes import sanitize_filename, validate_resume
from tests.helpers import PDF_BYTES

MB = 1024 * 1024


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("resume.pdf", "resume.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\ada\\cv.docx", "cv.docx"),
        ("my\x00cv\n.pdf", "mycv.pdf"),
        ('evil"; name=x.pdf', "evil_ name_x.pdf"),
        ("Résumé.pdf", "Résumé.pdf"),
        ("", "resume"),
        (None, "resume"),
        ("...", "resume"),
    ],
)
def test_sanitize_filename(raw: str | None, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_sanitize_filename_truncates_but_keeps_extension() -> None:
    name = sanitize_filename("a" * 500 + ".pdf")
    assert len(name) <= 200
    assert name.endswith(".pdf")


def test_valid_pdf() -> None:
    result = validate_resume(io.BytesIO(PDF_BYTES), "CV.PDF", max_bytes=MB)
    assert result.resume_type.content_type == "application/pdf"
    assert result.size_bytes == len(PDF_BYTES)
    assert result.filename == "CV.PDF"


def test_leaves_stream_at_start() -> None:
    stream = io.BytesIO(PDF_BYTES)
    validate_resume(stream, "cv.pdf", max_bytes=MB)
    assert stream.tell() == 0


@pytest.mark.parametrize(
    ("content", "filename"),
    [
        (PDF_BYTES, "cv.txt"),
        (PDF_BYTES, "cv"),
        (b"PK\x03\x04rest", "cv.pdf"),  # a zip pretending to be a PDF
        (b"%PDF-1.4", "cv.docx"),  # a PDF pretending to be a DOCX
        (b"", "cv.pdf"),
    ],
)
def test_rejects(content: bytes, filename: str) -> None:
    with pytest.raises(InvalidInputError):
        validate_resume(io.BytesIO(content), filename, max_bytes=MB)


def test_rejects_too_large() -> None:
    with pytest.raises(InvalidInputError, match="MB or smaller"):
        validate_resume(io.BytesIO(PDF_BYTES + b"0" * MB), "cv.pdf", max_bytes=MB)
