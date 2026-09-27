import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EmailOutbox, Lead, LeadState


class LeadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, lead: Lead, outbox: Sequence[EmailOutbox]) -> None:
        self.db.add(lead)
        # Outbox rows reference the lead by FK with no ORM relationship, so flush the lead
        # first to guarantee INSERT order. Both stay in the caller's transaction.
        self.db.flush()
        self.db.add_all(outbox)

    def get(self, lead_id: uuid.UUID, *, for_update: bool = False) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id)
        if for_update:
            # `of=Lead` keeps the lock off the joined users row.
            stmt = stmt.with_for_update(of=Lead)
        return self.db.scalars(stmt).unique().one_or_none()

    def list(
        self, *, state: LeadState | None, offset: int, limit: int
    ) -> tuple[Sequence[Lead], int]:
        filters = [Lead.state == state] if state else []
        total = self.db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
        items = (
            self.db.scalars(
                select(Lead)
                .where(*filters)
                .order_by(Lead.created_at.desc(), Lead.id.desc())
                .offset(offset)
                .limit(limit)
            )
            .unique()
            .all()
        )
        return items, total
