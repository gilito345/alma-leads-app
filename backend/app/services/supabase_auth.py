"""A small client for the parts of Supabase Auth (GoTrue) this app uses.

Password sign-in and token refresh use the publishable key; creating and deleting users uses
the admin API with the secret key. Through the Supabase API gateway, an `sb_...` key in the
`apikey` header is enough; legacy JWT keys are also sent as a bearer token.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: uuid.UUID


class SupabaseAuthError(Exception):
    """Supabase Auth rejected the request or couldn't be reached."""

    def __init__(self, message: str, *, status: int = 502, code: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class InvalidCredentialsError(SupabaseAuthError):
    pass


class InvalidRefreshTokenError(SupabaseAuthError):
    pass


class EmailTakenError(SupabaseAuthError):
    pass


class WeakPasswordError(SupabaseAuthError):
    pass


class SupabaseAuth(Protocol):
    def sign_in_with_password(self, email: str, password: str) -> AuthSession: ...

    def refresh_session(self, refresh_token: str) -> AuthSession: ...

    def sign_out(self, access_token: str) -> None: ...

    def admin_create_user(self, email: str, password: str, full_name: str) -> uuid.UUID: ...

    def admin_delete_user(self, user_id: uuid.UUID) -> None: ...


def key_headers(key: str) -> dict[str, str]:
    headers = {"apikey": key}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    return headers


class SupabaseAuthClient:
    def __init__(
        self,
        base_url: str,
        publishable_key: str,
        secret_key: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._auth_url = f"{base_url.rstrip('/')}/auth/v1"
        self._publishable_key = publishable_key
        self._secret_key = secret_key
        self._client = client or httpx.Client(timeout=10.0)

    @classmethod
    def from_settings(cls, settings: Settings) -> "SupabaseAuthClient":
        return cls(
            settings.supabase_api_url,
            settings.supabase_publishable_key.get_secret_value(),
            settings.supabase_secret_key.get_secret_value(),
        )

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        response = self._post(
            "/token?grant_type=password",
            {"email": email, "password": password},
            key_headers(self._publishable_key),
        )
        if response.status_code in (400, 401):
            raise InvalidCredentialsError("Invalid login credentials", status=401)
        return self._session(response)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        response = self._post(
            "/token?grant_type=refresh_token",
            {"refresh_token": refresh_token},
            key_headers(self._publishable_key),
        )
        if response.status_code in (400, 401, 403):
            raise InvalidRefreshTokenError("Session expired", status=401)
        return self._session(response)

    def sign_out(self, access_token: str) -> None:
        headers = {"apikey": self._publishable_key, "Authorization": f"Bearer {access_token}"}
        try:
            self._client.post(f"{self._auth_url}/logout?scope=local", headers=headers)
        except httpx.HTTPError:
            logger.warning("Supabase sign-out failed", exc_info=True)

    def admin_create_user(self, email: str, password: str, full_name: str) -> uuid.UUID:
        response = self._post(
            "/admin/users",
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {"full_name": full_name},
            },
            key_headers(self._secret_key),
        )
        if response.status_code == 422 or response.status_code == 400:
            code = _error_code(response)
            if code == "email_exists" or "already" in response.text.lower():
                raise EmailTakenError("Email already registered", status=409, code=code)
            if code == "weak_password":
                raise WeakPasswordError("Password is too weak", status=422, code=code)
        _raise_for_status(response)
        return uuid.UUID(str(response.json()["id"]))

    def admin_delete_user(self, user_id: uuid.UUID) -> None:
        try:
            response = self._client.delete(
                f"{self._auth_url}/admin/users/{user_id}", headers=key_headers(self._secret_key)
            )
            _raise_for_status(response)
        except (httpx.HTTPError, SupabaseAuthError):
            logger.warning("Could not delete Supabase user %s", user_id, exc_info=True)

    def _post(self, path: str, body: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        try:
            return self._client.post(f"{self._auth_url}{path}", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise SupabaseAuthError(f"Could not reach Supabase Auth: {exc}") from exc

    def _session(self, response: httpx.Response) -> AuthSession:
        _raise_for_status(response)
        data = response.json()
        return AuthSession(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=int(data.get("expires_in", 3600)),
            user_id=uuid.UUID(str(data["user"]["id"])),
        )


def _error_code(response: httpx.Response) -> str | None:
    try:
        data = response.json()
    except ValueError:
        return None
    code = data.get("error_code") or data.get("error")
    return str(code) if code else None


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    if response.status_code == 429:
        raise SupabaseAuthError(
            "Too many requests to Supabase Auth", status=429, code="rate_limited"
        )
    logger.error("Supabase Auth returned %s: %s", response.status_code, response.text[:500])
    raise SupabaseAuthError(
        f"Supabase Auth error ({response.status_code})", code=_error_code(response)
    )
