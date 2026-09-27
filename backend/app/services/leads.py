import logging
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.models import (
    ALLOWED_TRANSITIONS,
    EmailKind,
    EmailOutbox,
    Lead,
    LeadState,
    User,
)
from app.repositories.leads import LeadRepository
from app.schemas.lead import LeadCreate
from app.services.resumes import validate_resume
from app.services.storage import ObjectNotFoundError, ObjectStorage

logger = logging.getLogger(__name__)


class LeadService:
    """Business rules for leads: creation (with resume + email queueing), listing, state."""

    def __init__(self, db: Session, storage: ObjectStorage, settings: Settings) -> None:
        self.db = db
        self.storage = storage
        self.settings = settings
        self.leads = LeadRepository(db)

    def create_lead(self, data: LeadCreate, resume: BinaryIO, resume_filename: str | None) -> Lead:
        validated = validate_resume(
            resume, resume_filename, max_bytes=self.settings.max_resume_bytes
        )

        lead_id = uuid.uuid4()
        object_key = f"leads/{lead_id}/{uuid.uuid4().hex}.{validated.resume_type.extension}"
        self.storage.put(
            object_key,
            resume,
            content_type=validated.resume_type.content_type,
            size=validated.size_bytes,
        )

        lead = Lead(
            id=lead_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=str(data.email).lower(),
            resume_object_key=object_key,
            resume_filename=validated.filename,
            resume_content_type=validated.resume_type.content_type,
            resume_size_bytes=validated.size_bytes,
            state=LeadState.PENDING,
        )
        outbox = [
            EmailOutbox(
                lead_id=lead_id, kind=EmailKind.PROSPECT_CONFIRMATION, recipient=lead.email
            ),
            EmailOutbox(
                lead_id=lead_id,
                kind=EmailKind.ATTORNEY_NOTIFICATION,
                recipient=str(self.settings.attorney_notification_email),
            ),
        ]

        try:
            self.leads.add(lead, outbox)
            self.db.commit()
        except Exception:
            self.db.rollback()
            self._delete_object_quietly(object_key)
            raise

        self.db.refresh(lead)
        logger.info("Lead created id=%s", lead.id)
        return lead

    def list_leads(
        self, *, state: LeadState | None, page: int, page_size: int
    ) -> tuple[list[Lead], int]:
        items, total = self.leads.list(
            state=state, offset=(page - 1) * page_size, limit=page_size
        )
        return list(items), total

    def get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = self.leads.get(lead_id)
        if lead is None:
            raise NotFoundError("Lead not found")
        return lead

    def update_state(self, lead_id: uuid.UUID, new_state: LeadState, actor: User) -> Lead:
        lead = self.leads.get(lead_id, for_update=True)
        if lead is None:
            raise NotFoundError("Lead not found")

        if lead.state == new_state:
            # Idempotent: two attorneys clicking the button at once both succeed.
            self.db.rollback()
            return lead

        if new_state not in ALLOWED_TRANSITIONS[lead.state]:
            self.db.rollback()
            raise ConflictError(
                f"Cannot change a lead from {lead.state.value} to {new_state.value}",
                code="invalid_state_transition",
            )

        lead.state = new_state
        if new_state is LeadState.REACHED_OUT:
            lead.reached_out_at = datetime.now(UTC)
            lead.reached_out_by = actor
        self.db.commit()
        self.db.refresh(lead)
        logger.info("Lead %s moved to %s by user=%s", lead.id, new_state.value, actor.id)
        return lead

    def open_resume(self, lead_id: uuid.UUID) -> tuple[Lead, Iterator[bytes]]:
        lead = self.get_lead(lead_id)
        try:
            return lead, self.storage.stream(lead.resume_object_key)
        except ObjectNotFoundError as exc:
            logger.error(
                "Resume object missing for lead=%s key=%s", lead.id, lead.resume_object_key
            )
            raise NotFoundError("Resume file not found") from exc

    def _delete_object_quietly(self, key: str) -> None:
        try:
            self.storage.delete(key)
        except Exception:
            logger.warning("Could not delete orphaned resume object %s", key, exc_info=True)
