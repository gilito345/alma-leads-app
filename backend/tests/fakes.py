"""In-memory stand-in for Supabase Auth, issuing real HS256 tokens the app can verify."""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.services.supabase_auth import (
    AuthSession,
    EmailTakenError,
    InvalidCredentialsError,
    InvalidLinkError,
    InvalidRefreshTokenError,
    LinkType,
    SignOutScope,
    UserNotFoundError,
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
        # email -> (id, password, name); password is None until an invite is accepted
        self.users: dict[str, tuple[uuid.UUID, str | None, str]] = {}
        self.confirmed: set[uuid.UUID] = set()
        self.links: dict[str, tuple[LinkType, uuid.UUID]] = {}  # token hash -> (type, user)
        self.refresh_tokens: dict[str, uuid.UUID] = {}
        self.signed_out: list[str] = []
        self.signed_out_scopes: list[SignOutScope] = []
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
        if entry is None or entry[1] is None or entry[1] != password:
            raise InvalidCredentialsError("Invalid login credentials", status=401)
        return self._session(entry[0])

    def refresh_session(self, refresh_token: str) -> AuthSession:
        user_id = self.refresh_tokens.pop(refresh_token, None)  # rotation: single use
        if user_id is None:
            raise InvalidRefreshTokenError("Session expired", status=401)
        return self._session(user_id)

    def sign_out(self, access_token: str, scope: SignOutScope = "local") -> None:
        self.signed_out.append(access_token)
        self.signed_out_scopes.append(scope)

    def admin_create_user(self, email: str, password: str | None, full_name: str) -> uuid.UUID:
        if email.lower() in self.users:
            raise EmailTakenError("Email already registered", status=409, code="email_exists")
        user_id = uuid.uuid4()
        self.users[email.lower()] = (user_id, password, full_name)
        if password is not None:
            self.confirmed.add(user_id)
        return user_id

    def admin_delete_user(self, user_id: uuid.UUID) -> None:
        self.deleted.append(user_id)
        self.users = {k: v for k, v in self.users.items() if v[0] != user_id}

    def admin_is_confirmed(self, user_id: uuid.UUID) -> bool:
        self._email_of(user_id)
        return user_id in self.confirmed

    def admin_set_password(self, user_id: uuid.UUID, password: str) -> None:
        email = self._email_of(user_id)
        _, _, name = self.users[email]
        self.users[email] = (user_id, password, name)

    def admin_generate_link(self, link_type: LinkType, email: str) -> str:
        entry = self.users.get(email.lower())
        if entry is None:
            raise UserNotFoundError("User not found", status=404, code="user_not_found")
        if link_type == "invite" and entry[0] in self.confirmed:
            raise EmailTakenError("Email already registered", status=409, code="email_exists")
        # Like Supabase, a new token replaces the user's previous one.
        self.links = {k: v for k, v in self.links.items() if v[1] != entry[0]}
        token_hash = secrets.token_hex(28)
        self.links[token_hash] = (link_type, entry[0])
        return token_hash

    def verify_link(self, link_type: LinkType, token_hash: str) -> AuthSession:
        link = self.links.get(token_hash)
        if link is None or link[0] != link_type:
            raise InvalidLinkError("Link is invalid or has expired", status=401)
        del self.links[token_hash]  # single use
        self.confirmed.add(link[1])
        return self._session(link[1])

    def token_for(self, email: str) -> str:
        """The live link token for `email` (what the emailed link would carry)."""
        user_id = self.users[email.lower()][0]
        return next(token for token, (_, uid) in self.links.items() if uid == user_id)

    def _email_of(self, user_id: uuid.UUID) -> str:
        for email, (uid, _, _) in self.users.items():
            if uid == user_id:
                return email
        raise UserNotFoundError("User not found", status=404, code="user_not_found")


class NoJwks:
    """Signing-key source for tests that only use HS256 tokens."""

    def get_signing_key_from_jwt(self, token: str) -> object:
        raise jwt.PyJWKClientError("JWKS not available in tests")
