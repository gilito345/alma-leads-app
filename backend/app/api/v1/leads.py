import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.api.deps import get_current_user, get_lead_service
from app.api.rate_limit import create_lead_limit, limiter
from app.models import LeadState, User
from app.schemas.lead import (
    LeadCreate,
    LeadCreated,
    LeadPage,
    LeadRead,
    LeadUpdate,
    ResumePreview,
)
from app.services.leads import LeadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=LeadCreated,
    summary="Submit a lead (public)",
)
@limiter.limit(create_lead_limit)
def create_lead(
    request: Request,
    first_name: Annotated[str, Form(max_length=200)],
    last_name: Annotated[str, Form(max_length=200)],
    email: Annotated[str, Form(max_length=320)],
    resume: Annotated[UploadFile, File(description="PDF, DOC or DOCX, up to 10 MB")],
    website: Annotated[str, Form(description="Honeypot. Leave empty.")] = "",
    service: LeadService = Depends(get_lead_service),
) -> LeadCreated:
    if website.strip():
        # A human never sees this field. Pretend success so the bot doesn't adapt.
        logger.info("Dropped submission that filled the honeypot field")
        return LeadCreated(id=uuid.uuid4(), created_at=datetime.now(UTC))

    try:
        data = LeadCreate(first_name=first_name, last_name=last_name, email=email)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    lead = service.create_lead(data, resume.file, resume.filename)
    return LeadCreated(id=lead.id, created_at=lead.created_at)


@router.get("", response_model=LeadPage, summary="List leads")
def list_leads(
    state: Annotated[LeadState | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    service: LeadService = Depends(get_lead_service),
    _: User = Depends(get_current_user),
) -> LeadPage:
    items, total = service.list_leads(state=state, page=page, page_size=page_size)
    return LeadPage(
        items=[LeadRead.from_model(lead) for lead in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{lead_id}", response_model=LeadRead, summary="Get a lead")
def get_lead(
    lead_id: uuid.UUID,
    service: LeadService = Depends(get_lead_service),
    _: User = Depends(get_current_user),
) -> LeadRead:
    return LeadRead.from_model(service.get_lead(lead_id))


@router.patch("/{lead_id}", response_model=LeadRead, summary="Update a lead's state")
def update_lead(
    lead_id: uuid.UUID,
    body: LeadUpdate,
    service: LeadService = Depends(get_lead_service),
    user: User = Depends(get_current_user),
) -> LeadRead:
    return LeadRead.from_model(service.update_state(lead_id, body.state, user))


@router.get("/{lead_id}/resume", summary="Download (or, for PDFs, view) a lead's resume")
def download_resume(
    lead_id: uuid.UUID,
    service: LeadService = Depends(get_lead_service),
    _: User = Depends(get_current_user),
    disposition: Annotated[
        Literal["attachment", "inline"],
        Query(description="`inline` lets the browser display a PDF; other types always download"),
    ] = "attachment",
) -> StreamingResponse:
    lead, chunks = service.open_resume(lead_id)
    # Only PDFs may render in the browser. Word files are never displayed inline, so a
    # browser can't be talked into interpreting an uploaded file as something else.
    inline = disposition == "inline" and lead.resume_content_type == "application/pdf"
    return StreamingResponse(
        chunks,
        media_type=lead.resume_content_type,
        headers={
            "Content-Disposition": content_disposition(lead.resume_filename, inline=inline),
            "Content-Length": str(lead.resume_size_bytes),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get(
    "/{lead_id}/resume/preview",
    response_model=ResumePreview,
    summary="How to show a lead's resume in the page (PDF, sanitized HTML, or none)",
)
def preview_resume(
    lead_id: uuid.UUID,
    service: LeadService = Depends(get_lead_service),
    _: User = Depends(get_current_user),
) -> ResumePreview:
    return service.resume_preview(lead_id)


def content_disposition(filename: str, *, inline: bool = False) -> str:
    ascii_name = filename.encode("ascii", "ignore").decode() or "resume"
    ascii_name = ascii_name.replace('"', "").replace("\\", "")
    kind = "inline" if inline else "attachment"
    return f"{kind}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"
