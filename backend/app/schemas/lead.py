import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models import Lead, LeadState

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class LeadCreate(BaseModel):
    """The text fields of the public form. The resume arrives as a separate file part."""

    first_name: Name
    last_name: Name
    email: EmailStr


class LeadCreated(BaseModel):
    """Public response to a submission: deliberately minimal."""

    id: uuid.UUID
    created_at: datetime


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str


class ResumeInfo(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class LeadRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    state: LeadState
    resume: ResumeInfo
    reached_out_at: datetime | None
    reached_out_by: UserSummary | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, lead: Lead) -> "LeadRead":
        return cls(
            id=lead.id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            state=lead.state,
            resume=ResumeInfo(
                filename=lead.resume_filename,
                content_type=lead.resume_content_type,
                size_bytes=lead.resume_size_bytes,
            ),
            reached_out_at=lead.reached_out_at,
            reached_out_by=(
                UserSummary.model_validate(lead.reached_out_by) if lead.reached_out_by else None
            ),
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )


class LeadUpdate(BaseModel):
    state: LeadState


class LeadPage(BaseModel):
    items: list[LeadRead]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
