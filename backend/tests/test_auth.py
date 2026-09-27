from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError
from app.main import create_app
from app.models import User
from app.services.auth import AuthService
from tests.helpers import ATTORNEY_PASSWORD


def login(client: TestClient, email: str, password: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


class TestLogin:
    def test_returns_bearer_token(self, client: TestClient, attorney: User, settings: Settings):
        response = login(client, "JANE@firm.test", ATTORNEY_PASSWORD)

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == settings.jwt_expires_minutes * 60
        claims = jwt.decode(
            body["access_token"], settings.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )
        assert claims["sub"] == str(attorney.id)

    def test_wrong_password(self, client: TestClient, attorney: User) -> None:
        response = login(client, attorney.email, "wrong-password")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"

    def test_unknown_email_gets_same_error(self, client: TestClient) -> None:
        response = login(client, "nobody@firm.test", ATTORNEY_PASSWORD)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"

    def test_inactive_user_cannot_log_in(
        self, client: TestClient, attorney: User, db: Session
    ) -> None:
        attorney.is_active = False
        db.merge(attorney)
        db.commit()
        assert login(client, attorney.email, ATTORNEY_PASSWORD).status_code == 401


class TestMe:
    def test_returns_current_user(
        self, client: TestClient, auth_headers: dict[str, str], attorney: User
    ) -> None:
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == attorney.email

    def test_expired_token_is_rejected(
        self, client: TestClient, attorney: User, settings: Settings
    ) -> None:
        past = datetime.now(UTC) - timedelta(hours=10)
        token = jwt.encode(
            {
                "sub": str(attorney.id),
                "iat": past,
                "exp": past + timedelta(hours=1),
                "type": "access",
            },
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    def test_token_signed_with_other_key_is_rejected(
        self, client: TestClient, attorney: User
    ) -> None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(attorney.id),
                "iat": now,
                "exp": now + timedelta(hours=1),
                "type": "access",
            },
            "some-other-secret-that-is-also-long-enough",
            algorithm="HS256",
        )
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


class TestCreateUser:
    def test_rejects_duplicate_email(self, db: Session, settings: Settings, attorney: User):
        with pytest.raises(ConflictError):
            AuthService(db, settings).create_user("Jane@Firm.test", "Other", "another-password-1")

    def test_rejects_short_password(self, db: Session, settings: Settings) -> None:
        with pytest.raises(ValueError, match="12 characters"):
            AuthService(db, settings).create_user("new@firm.test", "New", "short")


def signup(client: TestClient, **overrides: str):
    body = {
        "email": "new@firm.test",
        "full_name": "New Attorney",
        "password": "a-long-enough-password",
    }
    body.update(overrides)
    return client.post("/api/v1/auth/signup", json=body)


@pytest.fixture
def client_with_invite_code(settings: Settings, storage) -> Iterator[TestClient]:
    configured = settings.model_copy(update={"attorney_signup_code": SecretStr("join-the-firm")})
    with TestClient(create_app(configured, storage=storage)) as test_client:
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
        token = response.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
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
