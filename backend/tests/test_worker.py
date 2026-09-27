from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.models import EmailKind, EmailOutbox, EmailStatus
from app.services.email import ConsoleEmailSender, EmailMessage, EmailSendError
from app.worker.outbox import OutboxProcessor, backoff_delay
from tests.helpers import lead_form, resume_file


class FailingSender:
    def __init__(self, *, retryable: bool) -> None:
        self.retryable = retryable
        self.calls = 0

    def send(self, message: EmailMessage, *, idempotency_key: str) -> str | None:
        self.calls += 1
        raise EmailSendError("provider unavailable", retryable=self.retryable)


class Clock:
    def __init__(self) -> None:
        self.now = datetime.now(UTC) + timedelta(seconds=1)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def lead_id(client: TestClient) -> str:
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())
    assert response.status_code == 201
    return str(response.json()["id"])


def outbox_rows(db: Session) -> list[EmailOutbox]:
    db.expire_all()
    return list(db.scalars(select(EmailOutbox).order_by(EmailOutbox.kind)).all())


def test_sends_queued_emails_and_marks_them_sent(
    lead_id: str, db: Session, settings: Settings
) -> None:
    sender = ConsoleEmailSender()
    processor = OutboxProcessor(get_sessionmaker(), sender, settings, clock=Clock())

    assert processor.process_batch() == 2

    rows = outbox_rows(db)
    assert {row.status for row in rows} == {EmailStatus.SENT}
    assert all(row.attempts == 1 and row.sent_at is not None for row in rows)

    by_recipient = {message.to: message for message in sender.sent}
    prospect = by_recipient["ada@example.com"]
    attorney = by_recipient["intake@firm.test"]
    assert prospect.subject == "We received your information"
    assert "Ada" in prospect.text
    assert attorney.subject == "New lead: Ada Lovelace"
    assert f"http://web.test/leads/{lead_id}" in attorney.html
    assert attorney.reply_to == "ada@example.com"

    # Nothing left to do on the next poll.
    assert processor.process_batch() == 0


def test_escapes_user_input_in_html(client: TestClient, settings: Settings) -> None:
    client.post(
        "/api/v1/leads",
        data=lead_form(first_name="<script>alert(1)</script>"),
        files=resume_file(),
    )
    sender = ConsoleEmailSender()
    OutboxProcessor(get_sessionmaker(), sender, settings, clock=Clock()).process_batch()

    html = next(m.html for m in sender.sent if m.to == "intake@firm.test")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_retryable_failure_is_rescheduled_with_backoff(
    lead_id: str, db: Session, settings: Settings
) -> None:
    clock = Clock()
    processor = OutboxProcessor(
        get_sessionmaker(), FailingSender(retryable=True), settings, clock=clock
    )

    processor.process_batch()

    for row in outbox_rows(db):
        assert row.status is EmailStatus.PENDING
        assert row.attempts == 1
        assert row.last_error == "provider unavailable"
        assert row.next_attempt_at == clock.now + backoff_delay(1)

    # Not due yet, so a second poll right away does nothing.
    assert processor.process_batch() == 0


def test_gives_up_after_max_attempts(lead_id: str, db: Session, settings: Settings) -> None:
    clock = Clock()
    sender = FailingSender(retryable=True)
    processor = OutboxProcessor(get_sessionmaker(), sender, settings, clock=clock)

    for _ in range(settings.email_max_attempts):
        processor.process_batch()
        clock.now += timedelta(days=1)

    rows = outbox_rows(db)
    assert {row.status for row in rows} == {EmailStatus.FAILED}
    assert all(row.attempts == settings.email_max_attempts for row in rows)
    assert processor.process_batch() == 0


def test_non_retryable_failure_fails_immediately(
    lead_id: str, db: Session, settings: Settings
) -> None:
    processor = OutboxProcessor(
        get_sessionmaker(), FailingSender(retryable=False), settings, clock=Clock()
    )
    processor.process_batch()
    assert {row.status for row in outbox_rows(db)} == {EmailStatus.FAILED}


def test_one_failure_does_not_block_the_other_email(
    lead_id: str, db: Session, settings: Settings
) -> None:
    class AttorneyInboxDown(ConsoleEmailSender):
        def send(self, message: EmailMessage, *, idempotency_key: str) -> str | None:
            if message.to == "intake@firm.test":
                raise EmailSendError("mailbox full", retryable=False)
            return super().send(message, idempotency_key=idempotency_key)

    OutboxProcessor(
        get_sessionmaker(), AttorneyInboxDown(), settings, clock=Clock()
    ).process_batch()

    status = {row.kind: row.status for row in outbox_rows(db)}
    assert status == {
        EmailKind.PROSPECT_CONFIRMATION: EmailStatus.SENT,
        EmailKind.ATTORNEY_NOTIFICATION: EmailStatus.FAILED,
    }


def test_backoff_grows_and_is_capped() -> None:
    assert backoff_delay(1) == timedelta(seconds=30)
    assert backoff_delay(2) == timedelta(seconds=60)
    assert backoff_delay(3) == timedelta(seconds=120)
    assert backoff_delay(50) == timedelta(hours=1)
