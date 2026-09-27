PDF_BYTES = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << >>\n%%EOF\n"
ATTORNEY_PASSWORD = "correct-horse-battery-staple"


def lead_form(**overrides: str) -> dict[str, str]:
    data = {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}
    data.update(overrides)
    return data


def resume_file(
    content: bytes = PDF_BYTES, filename: str = "resume.pdf", content_type: str = "application/pdf"
) -> dict[str, tuple[str, bytes, str]]:
    return {"resume": (filename, content, content_type)}
