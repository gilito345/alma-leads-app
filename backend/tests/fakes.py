"""In-memory stand-in for Supabase Auth, issuing real HS256 tokens the app can verify."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.services.supabase_auth import (
    AuthSession,
    EmailTakenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

TEST_JWT_SECRET = "test-supabase-jwt-secret-long-enough-for-hs256"


def make_access_token(
    user_id: uuid.UUID,
    *,
    secret: str = TEST_JWT_SECRET,
    expires_in: int = 3600,
    audience: str = "authenticated",
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "aud": audience,
            "role": "authenticated",
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
        },
        secret,
        algorithm="HS256",
    )


class FakeSupabaseAuth:
    def __init__(self) -> None:
        self.users: dict[str, tuple[uuid.UUID, str, str]] = {}  # email -> (id, password, name)
        self.refresh_tokens: dict[str, uuid.UUID] = {}
        self.signed_out: list[str] = []
        self.deleted: list[uuid.UUID] = []

    def _session(self, user_id: uuid.UUID) -> AuthSession:
        refresh_token = secrets.token_urlsafe(16)
        self.refresh_tokens[refresh_token] = user_id
        return AuthSession(
            access_token=make_access_token(user_id),
            refresh_token=refresh_token,
            expires_in=3600,
            user_id=user_id,
        )

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        entry = self.users.get(email.lower())
        if entry is None or entry[1] != password:
            raise InvalidCredentialsError("Invalid login credentials", status=401)
        return self._session(entry[0])

    def refresh_session(self, refresh_token: str) -> AuthSession:
        user_id = self.refresh_tokens.pop(refresh_token, None)  # rotation: single use
        if user_id is None:
            raise InvalidRefreshTokenError("Session expired", status=401)
        return self._session(user_id)

    def sign_out(self, access_token: str) -> None:
        self.signed_out.append(access_token)

    def admin_create_user(self, email: str, password: str, full_name: str) -> uuid.UUID:
        if email.lower() in self.users:
            raise EmailTakenError("Email already registered", status=409, code="email_exists")
        user_id = uuid.uuid4()
        self.users[email.lower()] = (user_id, password, full_name)
        return user_id

    def admin_delete_user(self, user_id: uuid.UUID) -> None:
        self.deleted.append(user_id)
        self.users = {k: v for k, v in self.users.items() if v[0] != user_id}


class NoJwks:
    """Signing-key source for tests that only use HS256 tokens."""

    def get_signing_key_from_jwt(self, token: str) -> object:
        raise jwt.PyJWKClientError("JWKS not available in tests")
