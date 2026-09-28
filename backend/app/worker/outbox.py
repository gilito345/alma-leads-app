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
from app.models import EmailKind, EmailOutbox, EmailStatus, Lead, User
from app.services.email import (
    EmailMessage,
    EmailSender,
    EmailSendError,
    render_account_email,
    render_email,
)
from app.services.supabase_auth import (
    EmailTakenError,
    LinkType,
    SupabaseAuth,
    SupabaseAuthClient,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

BASE_BACKOFF_SECONDS = 30
MAX_BACKOFF_SECONDS = 60 * 60

_LINK_TYPES: dict[EmailKind, LinkType] = {
    EmailKind.ATTORNEY_INVITE: "invite",
    EmailKind.PASSWORD_RESET: "recovery",
}


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
        supabase_auth: SupabaseAuth | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.session_factory = session_factory
        self.sender = sender
        self.settings = settings
        self.supabase_auth = supabase_auth or SupabaseAuthClient.from_settings(settings)
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
            message = self._render(db, row)
            row.provider_message_id = self.sender.send(message, idempotency_key=str(row.id))
        except Exception as exc:
            retryable = exc.retryable if isinstance(exc, EmailSendError) else True
            row.last_error = str(exc)[:2000]
            if retryable and row.attempts < self.settings.email_max_attempts:
                row.next_attempt_at = self.clock() + backoff_delay(row.attempts)
                logger.warning(
                    "Email %s (%s) failed on attempt %d, retrying at %s: %s",
                    row.id,
                    row.kind.value,
                    row.attempts,
                    row.next_attempt_at,
                    exc,
                )
            else:
                row.status = EmailStatus.FAILED
                logger.error(
                    "Email %s (%s) for %s failed permanently after %d attempt(s): %s",
                    row.id,
                    row.kind.value,
                    _subject(row),
                    row.attempts,
                    exc,
                )
            return

        row.status = EmailStatus.SENT
        row.sent_at = self.clock()
        row.last_error = None
        logger.info("Email %s (%s) sent for %s", row.id, row.kind.value, _subject(row))

    def _render(self, db: Session, row: EmailOutbox) -> EmailMessage:
        if row.lead_id is not None:
            lead = db.get(Lead, row.lead_id)
            if lead is None:  # pragma: no cover - FK cascade makes this unreachable
                raise EmailSendError("Lead no longer exists", retryable=False)
            return render_email(row.kind, lead, row.recipient, self.settings)

        user = db.get(User, row.user_id) if row.user_id is not None else None
        if user is None or not user.is_active:
            raise EmailSendError("Account no longer exists or is deactivated", retryable=False)
        # The link is minted now rather than when the email was queued, so no usable token
        # ever sits in the database. A retry mints a fresh one, which replaces the old one.
        try:
            token_hash = self.supabase_auth.admin_generate_link(_LINK_TYPES[row.kind], user.email)
        except EmailTakenError as exc:
            raise EmailSendError("Invite was already accepted", retryable=False) from exc
        except UserNotFoundError as exc:
            raise EmailSendError("Supabase Auth user no longer exists", retryable=False) from exc
        return render_account_email(row.kind, user, token_hash, self.settings)


def _subject(row: EmailOutbox) -> str:
    return f"lead={row.lead_id}" if row.lead_id is not None else f"user={row.user_id}"
