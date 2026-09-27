"""Delivers queued emails from the `email_outbox` table.

Rows are claimed with `SELECT ... FOR UPDATE SKIP LOCKED`, so any number of workers can run
side by side without sending the same email twice.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.models import EmailOutbox, EmailStatus, Lead
from app.services.email import EmailSender, EmailSendError, render_email

logger = logging.getLogger(__name__)

BASE_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 60 * 60


def backoff_delay(attempts: int) -> timedelta:
    """30s, 60s, 120s, ... capped at an hour."""
    seconds = min(BASE_BACKOFF_SECONDS * 2 ** max(attempts - 1, 0), MAX_BACKOFF_SECONDS)
    return timedelta(seconds=seconds)


class OutboxProcessor:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        sender: EmailSender,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.session_factory = session_factory
        self.sender = sender
        self.settings = settings
        self.clock = clock

    def process_batch(self) -> int:
        """Send one batch of due emails. Returns how many rows were processed."""
        with self.session_factory() as db:
            rows = db.scalars(
                select(EmailOutbox)
                .where(
                    EmailOutbox.status == EmailStatus.PENDING,
                    EmailOutbox.next_attempt_at <= self.clock(),
                )
                .order_by(EmailOutbox.next_attempt_at)
                .limit(self.settings.worker_batch_size)
                .with_for_update(skip_locked=True)
            ).all()

            for row in rows:
                self._deliver(db, row)
            db.commit()
            return len(rows)

    def _deliver(self, db: Session, row: EmailOutbox) -> None:
        row.attempts += 1
        try:
            lead = db.get(Lead, row.lead_id)
            if lead is None:  # pragma: no cover - FK cascade makes this unreachable
                raise EmailSendError("Lead no longer exists", retryable=False)
            message = render_email(row.kind, lead, row.recipient, self.settings)
            row.provider_message_id = self.sender.send(message, idempotency_key=str(row.id))
        except Exception as exc:
            retryable = exc.retryable if isinstance(exc, EmailSendError) else True
            row.last_error = str(exc)[:2000]
            if retryable and row.attempts < self.settings.email_max_attempts:
                row.next_attempt_at = self.clock() + backoff_delay(row.attempts)
                logger.warning(
                    "Email %s (%s) failed on attempt %d, retrying at %s: %s",
                    row.id, row.kind.value, row.attempts, row.next_attempt_at, exc,
                )
            else:
                row.status = EmailStatus.FAILED
                logger.error(
                    "Email %s (%s) to lead=%s failed permanently after %d attempt(s): %s",
                    row.id, row.kind.value, row.lead_id, row.attempts, exc,
                )
            return

        row.status = EmailStatus.SENT
        row.sent_at = self.clock()
        row.last_error = None
        logger.info("Email %s (%s) sent for lead=%s", row.id, row.kind.value, row.lead_id)
