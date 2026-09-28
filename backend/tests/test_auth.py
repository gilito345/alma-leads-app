import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, InvalidInputError
from app.db.session import get_sessionmaker
from app.models import EmailKind, EmailOutbox, User
from app.services.auth import AuthService
from app.services.email import ConsoleEmailSender, EmailMessage
from app.worker.outbox import OutboxProcessor
from tests.fakes import FakeSupabaseAuth, make_access_token
from tests.helpers import ATTORNEY_PASSWORD


def login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLogin:
    def test_returns_supabase_session(self, client: TestClient, attorney: User) -> None:
        response = login(client, "JANE@firm.test", ATTORNEY_PASSWORD)

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["refresh_token"]
        assert body["expires_in"] == 3600
        me = client.get("/api/v1/auth/me", headers=bearer(body["access_token"]))
        assert me.json()["id"] == str(attorney.id)

    def test_wrong_password(self, client: TestClient, attorney: User) -> None:
        response = login(client, attorney.email, "wrong-password")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"

    def test_unknown_email_gets_same_error(self, client: TestClient) -> None:
        response = login(client, "nobody@firm.test", ATTORNEY_PASSWORD)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"

    def test_supabase_user_who_is_not_an_attorney_is_refused(
        self, client: TestClient, supabase_auth: FakeSupabaseAuth
    ) -> None:
        # Exists in Supabase Auth (e.g. created in Studio) but has no attorney record.
        supabase_auth.admin_create_user("outsider@firm.test", "some-long-password", "Outsider")
        response = login(client, "outsider@firm.test", "some-long-password")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"
        assert len(supabase_auth.signed_out) == 1

    def test_inactive_attorney_cannot_log_in(
        self, client: TestClient, attorney: User, auth_service: AuthService
    ) -> None:
        attorney.is_active = False
        auth_service.db.commit()
        assert login(client, attorney.email, ATTORNEY_PASSWORD).status_code == 401


class TestRefreshAndLogout:
    def test_refresh_returns_a_new_session(self, client: TestClient, attorney: User) -> None:
        first = login(client, attorney.email, ATTORNEY_PASSWORD).json()

        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
        )

        assert response.status_code == 200
        second = response.json()
        assert second["refresh_token"] != first["refresh_token"]
        assert client.get("/api/v1/auth/me", headers=bearer(second["access_token"])).is_success

    def test_used_refresh_token_is_rejected(self, client: TestClient, attorney: User) -> None:
        token = login(client, attorney.email, ATTORNEY_PASSWORD).json()["refresh_token"]
        client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "session_expired"

    def test_logout_signs_out_of_supabase(
        self, client: TestClient, auth_headers: dict[str, str], supabase_auth: FakeSupabaseAuth
    ) -> None:
        assert client.post("/api/v1/auth/logout", headers=auth_headers).status_code == 204
        assert supabase_auth.signed_out == [auth_headers["Authorization"].removeprefix("Bearer ")]


class TestTokens:
    def test_me_requires_a_token(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_expired_token_is_rejected(self, client: TestClient, attorney: User) -> None:
        token = make_access_token(attorney.id, expires_in=-60)
        assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401

    def test_token_signed_with_other_key_is_rejected(
        self, client: TestClient, attorney: User
    ) -> None:
        token = make_access_token(attorney.id, secret="some-other-secret-that-is-long-enough")
        assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401

    def test_token_for_wrong_audience_is_rejected(self, client: TestClient, attorney: User) -> None:
        token = make_access_token(attorney.id, audience="anon")
        assert client.get("/api/v1/auth/me", headers=bearer(token)).status_code == 401

    def test_valid_token_for_non_attorney_is_forbidden(self, client: TestClient) -> None:
        token = make_access_token(uuid.uuid4())
        response = client.get("/api/v1/auth/me", headers=bearer(token))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_an_attorney"


class TestCreateUser:
    def test_creates_supabase_identity_and_attorney(
        self, auth_service: AuthService, supabase_auth: FakeSupabaseAuth
    ) -> None:
        user = auth_service.create_user("New@Firm.test", "  New Attorney ", "a-long-enough-pass")
        assert user.email == "new@firm.test"
        assert user.full_name == "New Attorney"
        assert supabase_auth.users["new@firm.test"][0] == user.id

    def test_rejects_duplicate_email(self, auth_service: AuthService, attorney: User) -> None:
        with pytest.raises(ConflictError):
            auth_service.create_user("Jane@Firm.test", "Other", "another-password-1")

    def test_rejects_short_password(self, auth_service: AuthService) -> None:
        with pytest.raises(InvalidInputError):
            auth_service.create_user("new@firm.test", "New", "short")

    def test_existing_supabase_identity_is_reported_as_taken(
        self, auth_service: AuthService, supabase_auth: FakeSupabaseAuth
    ) -> None:
        supabase_auth.admin_create_user("taken@firm.test", "a-long-enough-pass", "Someone")
        with pytest.raises(ConflictError):
            auth_service.create_user("taken@firm.test", "New", "a-long-enough-pass")


NEW_PASSWORD = "a-brand-new-long-password"


def outbox_rows(db: Session, kind: EmailKind) -> list[EmailOutbox]:
    db.expire_all()
    return list(db.scalars(select(EmailOutbox).where(EmailOutbox.kind == kind)).all())


def deliver_emails(settings: Settings, supabase_auth: FakeSupabaseAuth) -> ConsoleEmailSender:
    """Run the worker once, the way it would pick up the queued emails."""
    sender = ConsoleEmailSender()
    OutboxProcessor(
        get_sessionmaker(),
        sender,
        settings,
        supabase_auth=supabase_auth,
        clock=lambda: datetime.now(UTC) + timedelta(seconds=1),
    ).process_batch()
    return sender


def link_token(message: EmailMessage, page: str) -> str:
    link = next(word for word in message.text.split() if f"{page}?token=" in word)
    return parse_qs(urlsplit(link).query)["token"][0]


def invite(client: TestClient, headers: dict[str, str], **overrides: str):
    body = {"email": "new@firm.test", "full_name": "New Attorney"}
    body.update(overrides)
    return client.post("/api/v1/auth/invites", json=body, headers=headers)


class TestInvites:
    def test_requires_a_signed_in_attorney(self, client: TestClient) -> None:
        assert invite(client, {}).status_code == 401

    def test_creates_a_pending_account_and_queues_the_email(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        response = invite(client, auth_headers, email="New@Firm.test", full_name=" New A ")

        assert response.status_code == 202, response.text
        assert response.json() == {
            "email": "new@firm.test",
            "full_name": "New A",
            "resent": False,
        }
        (row,) = outbox_rows(db, EmailKind.ATTORNEY_INVITE)
        user_id = supabase_auth.users["new@firm.test"][0]
        assert row.user_id == user_id
        assert row.lead_id is None
        assert row.recipient == "new@firm.test"
        assert user_id not in supabase_auth.confirmed
        # No password yet, so nobody can sign in as them before they accept.
        assert login(client, "new@firm.test", "any-guess-at-all").status_code == 401

    def test_accepting_sets_the_password_and_signs_in(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        settings: Settings,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        invite(client, auth_headers)
        sender = deliver_emails(settings, supabase_auth)
        (message,) = [m for m in sender.sent if m.to == "new@firm.test"]
        assert message.subject == "You're invited to the leads dashboard"
        assert "http://web.test/accept-invite?token=" in message.html
        assert "expires in 24 hours" in message.text
        token = link_token(message, "/accept-invite")

        response = client.post(
            "/api/v1/auth/invites/accept", json={"token": token, "password": NEW_PASSWORD}
        )

        assert response.status_code == 200, response.text
        me = client.get("/api/v1/auth/me", headers=bearer(response.json()["access_token"]))
        assert me.json()["email"] == "new@firm.test"
        assert me.json()["full_name"] == "New Attorney"
        assert login(client, "new@firm.test", NEW_PASSWORD).status_code == 200

        reused = client.post(
            "/api/v1/auth/invites/accept", json={"token": token, "password": NEW_PASSWORD}
        )
        assert reused.status_code == 401
        assert reused.json()["error"]["code"] == "invalid_link"

    def test_reinviting_a_pending_invitee_sends_a_new_link(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        db: Session,
        settings: Settings,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        invite(client, auth_headers)
        deliver_emails(settings, supabase_auth)
        first_token = supabase_auth.token_for("new@firm.test")

        response = invite(client, auth_headers, email="NEW@firm.test")

        assert response.status_code == 202
        assert response.json()["resent"] is True
        assert len(outbox_rows(db, EmailKind.ATTORNEY_INVITE)) == 2
        deliver_emails(settings, supabase_auth)
        accept_old = client.post(
            "/api/v1/auth/invites/accept", json={"token": first_token, "password": NEW_PASSWORD}
        )
        assert accept_old.status_code == 401

    def test_inviting_an_existing_attorney_is_a_conflict(
        self, client: TestClient, auth_headers: dict[str, str], attorney: User
    ) -> None:
        response = invite(client, auth_headers, email="JANE@firm.test")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "email_taken"

    def test_inviting_a_supabase_identity_without_attorney_record_is_a_conflict(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        supabase_auth.admin_create_user("outsider@firm.test", "some-long-password", "Outsider")
        assert invite(client, auth_headers, email="outsider@firm.test").status_code == 409

    def test_short_password_is_rejected_without_using_up_the_link(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        settings: Settings,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        invite(client, auth_headers)
        deliver_emails(settings, supabase_auth)
        token = supabase_auth.token_for("new@firm.test")

        short = client.post(
            "/api/v1/auth/invites/accept", json={"token": token, "password": "short"}
        )
        assert short.status_code == 422
        assert short.json()["error"]["details"][0]["field"] == "password"

        ok = client.post(
            "/api/v1/auth/invites/accept", json={"token": token, "password": NEW_PASSWORD}
        )
        assert ok.status_code == 200

    def test_unknown_token_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/invites/accept", json={"token": "nope", "password": NEW_PASSWORD}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_link"

    def test_signup_endpoints_are_gone(self, client: TestClient) -> None:
        assert client.get("/api/v1/auth/signup").status_code in (404, 405)
        body = {"email": "x@firm.test", "full_name": "X", "password": NEW_PASSWORD}
        assert client.post("/api/v1/auth/signup", json=body).status_code in (404, 405)


def request_reset(client: TestClient, email: str):
    return client.post("/api/v1/auth/password-reset", json={"email": email})


class TestPasswordReset:
    def test_unknown_email_gets_the_same_answer_and_nothing_is_sent(
        self, client: TestClient, db: Session, attorney: User
    ) -> None:
        known = request_reset(client, attorney.email)
        unknown = request_reset(client, "nobody@firm.test")

        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()
        (row,) = outbox_rows(db, EmailKind.PASSWORD_RESET)
        assert row.user_id == attorney.id

    def test_repeat_requests_within_a_minute_send_one_email(
        self, client: TestClient, db: Session, attorney: User
    ) -> None:
        for _ in range(3):
            assert request_reset(client, "Jane@Firm.test").status_code == 202
        assert len(outbox_rows(db, EmailKind.PASSWORD_RESET)) == 1

    def test_deactivated_attorney_gets_no_email(
        self, client: TestClient, db: Session, attorney: User, auth_service: AuthService
    ) -> None:
        attorney.is_active = False
        auth_service.db.commit()
        assert request_reset(client, attorney.email).status_code == 202
        assert outbox_rows(db, EmailKind.PASSWORD_RESET) == []

    def test_reset_sets_the_new_password_and_signs_out_other_sessions(
        self,
        client: TestClient,
        attorney: User,
        settings: Settings,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        request_reset(client, attorney.email)
        sender = deliver_emails(settings, supabase_auth)
        (message,) = sender.sent
        assert message.subject == "Reset your password"
        token = link_token(message, "/reset-password")

        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "password": NEW_PASSWORD},
        )

        assert response.status_code == 200, response.text
        assert client.get(
            "/api/v1/auth/me", headers=bearer(response.json()["access_token"])
        ).is_success
        assert supabase_auth.signed_out_scopes == ["others"]
        assert login(client, attorney.email, ATTORNEY_PASSWORD).status_code == 401
        assert login(client, attorney.email, NEW_PASSWORD).status_code == 200

    def test_reset_token_cannot_accept_an_invite(
        self,
        client: TestClient,
        attorney: User,
        settings: Settings,
        supabase_auth: FakeSupabaseAuth,
    ) -> None:
        request_reset(client, attorney.email)
        deliver_emails(settings, supabase_auth)
        token = supabase_auth.token_for(attorney.email)
        response = client.post(
            "/api/v1/auth/invites/accept", json={"token": token, "password": NEW_PASSWORD}
        )
        assert response.status_code == 401
