from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_sessionmaker
from app.models import EmailKind, EmailOutbox, EmailStatus, User
from app.services.email import ConsoleEmailSender, EmailMessage, EmailSendError
from app.services.supabase_auth import SupabaseAuthError
from app.worker.outbox import OutboxProcessor, backoff_delay
from tests.fakes import FakeSupabaseAuth
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
    # The resume is only reachable from the dashboard, so the email doesn't name the file.
    assert "resume.pdf" not in attorney.html + attorney.text
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


class TestAccountEmails:
    @pytest.fixture
    def invitee(self, db: Session, supabase_auth: FakeSupabaseAuth) -> User:
        user_id = supabase_auth.admin_create_user("new@firm.test", None, "New Attorney")
        user = User(id=user_id, email="new@firm.test", full_name="New Attorney")
        db.add(user)
        db.flush()
        db.add(EmailOutbox(user_id=user.id, kind=EmailKind.ATTORNEY_INVITE, recipient=user.email))
        db.commit()
        return user

    def test_invite_link_is_minted_at_send_time(
        self, invitee: User, db: Session, settings: Settings, supabase_auth: FakeSupabaseAuth
    ) -> None:
        assert supabase_auth.links == {}  # nothing usable exists until the worker sends
        sender = ConsoleEmailSender()
        processor = OutboxProcessor(
            get_sessionmaker(), sender, settings, supabase_auth=supabase_auth, clock=Clock()
        )

        assert processor.process_batch() == 1

        (row,) = outbox_rows(db)
        assert row.status == EmailStatus.SENT
        (message,) = sender.sent
        assert supabase_auth.token_for("new@firm.test") in message.text

    def test_invite_already_accepted_fails_without_retrying(
        self, invitee: User, db: Session, settings: Settings, supabase_auth: FakeSupabaseAuth
    ) -> None:
        supabase_auth.confirmed.add(invitee.id)
        processor = OutboxProcessor(
            get_sessionmaker(),
            ConsoleEmailSender(),
            settings,
            supabase_auth=supabase_auth,
            clock=Clock(),
        )

        processor.process_batch()

        (row,) = outbox_rows(db)
        assert row.status == EmailStatus.FAILED
        assert row.attempts == 1
        assert "already accepted" in (row.last_error or "")

    def test_supabase_outage_is_retried(
        self, invitee: User, db: Session, settings: Settings, supabase_auth: FakeSupabaseAuth
    ) -> None:
        def unavailable(*_: object) -> str:
            raise SupabaseAuthError("Could not reach Supabase Auth")

        supabase_auth.admin_generate_link = unavailable  # type: ignore[method-assign]
        processor = OutboxProcessor(
            get_sessionmaker(),
            ConsoleEmailSender(),
            settings,
            supabase_auth=supabase_auth,
            clock=Clock(),
        )

        processor.process_batch()

        (row,) = outbox_rows(db)
        assert row.status == EmailStatus.PENDING
        assert row.attempts == 1
