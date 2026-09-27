import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.user import User


class LeadState(enum.StrEnum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"


# The only state changes an attorney may make. Anything else is rejected with 409.
ALLOWED_TRANSITIONS: dict[LeadState, frozenset[LeadState]] = {
    LeadState.PENDING: frozenset({LeadState.REACHED_OUT}),
    LeadState.REACHED_OUT: frozenset(),
}


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_state_created_at", "state", "created_at"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    resume_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    resume_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    resume_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resume_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    state: Mapped[LeadState] = mapped_column(
        Enum(LeadState, name="lead_state"),
        nullable=False,
        default=LeadState.PENDING,
        server_default=LeadState.PENDING.value,
    )
    reached_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reached_out_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    reached_out_by: Mapped[User | None] = relationship(lazy="joined")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
