import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailKind(enum.StrEnum):
    PROSPECT_CONFIRMATION = "PROSPECT_CONFIRMATION"
    ATTORNEY_NOTIFICATION = "ATTORNEY_NOTIFICATION"


class EmailStatus(enum.StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailOutbox(Base):
    """An email waiting to be sent (or already sent) by the worker.

    Rows are written in the same transaction as the lead, so an email is queued if and only
    if its lead was saved. See docs/DESIGN.md, "Email: transactional outbox".
    """

    __tablename__ = "email_outbox"
    __table_args__ = (Index("ix_email_outbox_status_next_attempt_at", "status", "next_attempt_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[EmailKind] = mapped_column(Enum(EmailKind, name="email_kind"), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status"),
        nullable=False,
        default=EmailStatus.PENDING,
        server_default=EmailStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_error: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
