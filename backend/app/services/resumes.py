"""Validation for uploaded resumes.

The client's filename and Content-Type are both attacker-controlled, so the file's type is
decided by its extension *and* confirmed by its leading bytes. The stored content type
comes from our own table, never from the request.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import BinaryIO

from app.core.errors import InvalidInputError


@dataclass(frozen=True)
class ResumeType:
    extension: str
    content_type: str
    signatures: tuple[bytes, ...]


RESUME_TYPES: dict[str, ResumeType] = {
    "pdf": ResumeType("pdf", "application/pdf", (b"%PDF-",)),
    "docx": ResumeType(
        "docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        (b"PK\x03\x04",),
    ),
    "doc": ResumeType("doc", "application/msword", (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)),
}

_SIGNATURE_BYTES = max(len(sig) for t in RESUME_TYPES.values() for sig in t.signatures)
_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.\- ()]+")


@dataclass(frozen=True)
class ValidatedResume:
    filename: str
    resume_type: ResumeType
    size_bytes: int


def sanitize_filename(raw: str | None) -> str:
    """Keep a display-safe basename: no paths, control characters or odd punctuation."""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = unicodedata.normalize("NFKC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(" .")
    if len(name) > 200:
        stem, _, ext = name.rpartition(".")
        name = f"{stem[:190]}.{ext}" if stem else name[:200]
    return name or "resume"


def validate_resume(file: BinaryIO, filename: str | None, *, max_bytes: int) -> ValidatedResume:
    safe_name = sanitize_filename(filename)
    extension = safe_name.rpartition(".")[2].lower() if "." in safe_name else ""
    resume_type = RESUME_TYPES.get(extension)
    if resume_type is None:
        raise InvalidInputError(
            "Resume must be a PDF, DOC or DOCX file",
            details=[{"field": "resume", "message": "Unsupported file type"}],
        )

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size == 0:
        raise InvalidInputError(
            "Resume file is empty", details=[{"field": "resume", "message": "File is empty"}]
        )
    if size > max_bytes:
        raise InvalidInputError(
            f"Resume must be {max_bytes // (1024 * 1024)} MB or smaller",
            details=[{"field": "resume", "message": "File is too large"}],
        )

    head = file.read(_SIGNATURE_BYTES)
    file.seek(0)
    if not any(head.startswith(sig) for sig in resume_type.signatures):
        raise InvalidInputError(
            "Resume content doesn't match its file type",
            details=[{"field": "resume", "message": "File content doesn't match its extension"}],
        )

    return ValidatedResume(filename=safe_name, resume_type=resume_type, size_bytes=size)
