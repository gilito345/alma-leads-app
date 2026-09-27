import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.core.errors import ConflictError, InvalidInputError
from app.main import create_app
from app.models import User
from app.services.auth import AuthService
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

    def test_token_for_wrong_audience_is_rejected(
        self, client: TestClient, attorney: User
    ) -> None:
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


def signup(client: TestClient, **overrides: str):
    body = {
        "email": "new@firm.test",
        "full_name": "New Attorney",
        "password": "a-long-enough-password",
    }
    body.update(overrides)
    return client.post("/api/v1/auth/signup", json=body)


@pytest.fixture
def client_with_invite_code(
    settings: Settings, storage, supabase_auth, token_verifier
) -> Iterator[TestClient]:
    configured = settings.model_copy(update={"attorney_signup_code": SecretStr("join-the-firm")})
    app = create_app(
        configured, storage=storage, supabase_auth=supabase_auth, token_verifier=token_verifier
    )
    with TestClient(app) as test_client:
        yield test_client


class TestSignup:
    def test_first_account_needs_no_code_and_is_signed_in(self, client: TestClient) -> None:
        assert client.get("/api/v1/auth/signup").json() == {
            "open": True,
            "invite_code_required": False,
            "enabled": True,
        }

        response = signup(client)

        assert response.status_code == 201, response.text
        me = client.get("/api/v1/auth/me", headers=bearer(response.json()["access_token"]))
        assert me.json()["email"] == "new@firm.test"
        assert me.json()["full_name"] == "New Attorney"

    def test_closed_after_first_account_without_code(
        self, client: TestClient, attorney: User
    ) -> None:
        assert client.get("/api/v1/auth/signup").json()["enabled"] is False
        response = signup(client)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "signup_closed"

    def test_invite_code_required_after_first_account(
        self, client_with_invite_code: TestClient, attorney: User
    ) -> None:
        client = client_with_invite_code
        assert client.get("/api/v1/auth/signup").json() == {
            "open": False,
            "invite_code_required": True,
            "enabled": True,
        }

        wrong = signup(client, invite_code="guess")
        assert wrong.status_code == 403
        assert wrong.json()["error"]["code"] == "invalid_invite_code"
        assert signup(client).status_code == 403

        assert signup(client, invite_code=" join-the-firm ").status_code == 201

    def test_duplicate_email_with_code(
        self, client_with_invite_code: TestClient, attorney: User
    ) -> None:
        response = signup(
            client_with_invite_code, email="JANE@firm.test", invite_code="join-the-firm"
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "email_taken"

    def test_short_password(self, client: TestClient) -> None:
        response = signup(client, password="short")
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "password"
