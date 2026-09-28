# ruff: noqa: E501 - the DOCX fixtures are XML strings
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.services import resume_preview
from app.services.resume_preview import docx_to_html
from tests.helpers import PDF_BYTES, lead_form, resume_file

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)
_DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rLink" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="javascript:alert(1)" TargetMode="External"/>'
    "</Relationships>"
)


def make_docx(*paragraphs: str, body_extra: str = "") -> bytes:
    """A minimal but valid DOCX with the given paragraphs."""
    runs = "".join(f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>' for p in paragraphs)
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{runs}{body_extra}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def upload(client: TestClient, content: bytes, filename: str, content_type: str) -> str:
    response = client.post(
        "/api/v1/leads", data=lead_form(), files=resume_file(content, filename, content_type)
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


class TestDocxToHtml:
    def test_converts_paragraphs(self) -> None:
        html = docx_to_html(make_docx("Ada Lovelace", "Analyst, 1843"))
        assert html == "<p>Ada Lovelace</p><p>Analyst, 1843</p>"

    def test_escapes_markup_and_drops_dangerous_links(self) -> None:
        link = '<w:hyperlink r:id="rLink"><w:r><w:t>click me</w:t></w:r></w:hyperlink>'
        html = docx_to_html(
            make_docx("&lt;script&gt;alert(1)&lt;/script&gt;", body_extra=f"<w:p>{link}</w:p>")
        )
        assert html is not None
        assert "<script" not in html
        assert "&lt;script&gt;" in html  # shown as text, not run
        assert "javascript:" not in html
        assert "click me" in html

    def test_rejects_zip_bombs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(resume_preview, "MAX_UNCOMPRESSED_BYTES", 100)
        assert docx_to_html(make_docx("x" * 500)) is None

    def test_corrupt_file_gives_no_preview(self) -> None:
        assert docx_to_html(b"PK\x03\x04" + b"\x00" * 64) is None


class TestPreviewEndpoint:
    def test_requires_an_attorney(self, client: TestClient) -> None:
        lead_id = upload(client, PDF_BYTES, "cv.pdf", "application/pdf")
        assert client.get(f"/api/v1/leads/{lead_id}/resume/preview").status_code == 401

    def test_pdf_is_embedded_as_is(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = upload(client, PDF_BYTES, "cv.pdf", "application/pdf")
        response = client.get(f"/api/v1/leads/{lead_id}/resume/preview", headers=auth_headers)
        assert response.json() == {"format": "pdf", "html": None}

    def test_docx_is_converted(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = upload(client, make_docx("Hello from a DOCX"), "cv.docx", DOCX_TYPE)
        response = client.get(f"/api/v1/leads/{lead_id}/resume/preview", headers=auth_headers)
        assert response.json() == {"format": "html", "html": "<p>Hello from a DOCX</p>"}

    def test_doc_has_no_preview(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        lead_id = upload(client, DOC_BYTES, "cv.doc", "application/msword")
        response = client.get(f"/api/v1/leads/{lead_id}/resume/preview", headers=auth_headers)
        assert response.json() == {"format": "unavailable", "html": None}


class TestInlineDisposition:
    def test_pdf_can_be_shown_inline(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        lead_id = upload(client, PDF_BYTES, "cv.pdf", "application/pdf")
        response = client.get(
            f"/api/v1/leads/{lead_id}/resume?disposition=inline", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.content == PDF_BYTES

    def test_download_is_the_default(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        lead_id = upload(client, PDF_BYTES, "cv.pdf", "application/pdf")
        response = client.get(f"/api/v1/leads/{lead_id}/resume", headers=auth_headers)
        assert response.headers["content-disposition"].startswith("attachment;")

    def test_word_files_always_download(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        lead_id = upload(client, make_docx("hi"), "cv.docx", DOCX_TYPE)
        response = client.get(
            f"/api/v1/leads/{lead_id}/resume?disposition=inline", headers=auth_headers
        )
        assert response.headers["content-disposition"].startswith("attachment;")
