from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError
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
