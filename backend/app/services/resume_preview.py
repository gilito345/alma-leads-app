"""Turn a stored resume into something the dashboard can show without a download.

- PDF: browsers render it natively, so the web app embeds the file itself.
- DOCX: converted to HTML with mammoth, then sanitized with an allow-list (nh3). The web app
  also shows it in a sandboxed iframe, so even a sanitizer gap couldn't run script.
- DOC (legacy binary Word): needs LibreOffice to read, so there's no preview; download it.

A DOCX is a zip file, so it's checked for zip bombs before anything is decompressed.
"""

import io
import logging
import zipfile
from typing import Literal

import mammoth
import nh3

logger = logging.getLogger(__name__)

PreviewFormat = Literal["pdf", "html", "unavailable"]

# A real resume's XML is a few hundred KB; refuse archives that would expand past this.
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_HTML_CHARS = 2 * 1024 * 1024

_ALLOWED_TAGS = {
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "em", "i", "u", "s",
    "sub", "sup", "ul", "ol", "li", "blockquote", "a", "table", "thead", "tbody", "tr",
    "td", "th",
}  # fmt: skip
_ALLOWED_ATTRIBUTES = {"a": {"href"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}


def preview_format(content_type: str) -> PreviewFormat:
    if content_type == "application/pdf":
        return "pdf"
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "html"
    return "unavailable"


def docx_to_html(data: bytes) -> str | None:
    """Sanitized HTML for a DOCX, or None if it can't be converted safely."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                logger.warning("DOCX preview refused: archive expands past the limit")
                return None
        result = mammoth.convert_to_html(
            io.BytesIO(data),
            # Skip embedded images: never decoded, and <img> isn't in the allow-list anyway.
            convert_image=mammoth.images.img_element(lambda _image: {}),
        )
    except Exception:
        logger.warning("DOCX preview failed", exc_info=True)
        return None

    html = nh3.clean(
        result.value,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )
    if len(html) > MAX_HTML_CHARS:
        logger.warning("DOCX preview refused: converted HTML is too large")
        return None
    return html
