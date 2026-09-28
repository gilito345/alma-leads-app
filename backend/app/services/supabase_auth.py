"""A small client for the parts of Supabase Auth (GoTrue) this app uses.

Password sign-in, token refresh and redeeming email links use the publishable key; managing
users and generating invite/recovery links uses the admin API with the secret key. Through the
Supabase API gateway, an `sb_...` key in the `apikey` header is enough; legacy JWT keys are
also sent as a bearer token.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Protocol

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


class UserNotFoundError(SupabaseAuthError):
    pass


class InvalidLinkError(SupabaseAuthError):
    """An invite or recovery token that is unknown, already used or expired."""


# The one-time email links this app generates: invites for new attorneys, password recovery.
LinkType = Literal["invite", "recovery"]
SignOutScope = Literal["local", "others", "global"]


class SupabaseAuth(Protocol):
    def sign_in_with_password(self, email: str, password: str) -> AuthSession: ...

    def refresh_session(self, refresh_token: str) -> AuthSession: ...

    def sign_out(self, access_token: str, scope: SignOutScope = "local") -> None: ...

    def admin_create_user(self, email: str, password: str | None, full_name: str) -> uuid.UUID: ...

    def admin_delete_user(self, user_id: uuid.UUID) -> None: ...

    def admin_is_confirmed(self, user_id: uuid.UUID) -> bool: ...

    def admin_set_password(self, user_id: uuid.UUID, password: str) -> None: ...

    def admin_generate_link(self, link_type: LinkType, email: str) -> str: ...

    def verify_link(self, link_type: LinkType, token_hash: str) -> AuthSession: ...


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

    def sign_out(self, access_token: str, scope: SignOutScope = "local") -> None:
        """Revoke this session ("local"), every other session ("others") or all of them."""
        headers = {"apikey": self._publishable_key, "Authorization": f"Bearer {access_token}"}
        try:
            self._client.post(f"{self._auth_url}/logout?scope={scope}", headers=headers)
        except httpx.HTTPError:
            logger.warning("Supabase sign-out failed", exc_info=True)

    def admin_create_user(self, email: str, password: str | None, full_name: str) -> uuid.UUID:
        """Create a user. Without a password the account stays unconfirmed until an invite
        link is redeemed; with one it is confirmed and can sign in right away."""
        body: dict[str, Any] = {"email": email, "user_metadata": {"full_name": full_name}}
        if password is not None:
            body |= {"password": password, "email_confirm": True}
        response = self._post("/admin/users", body, key_headers(self._secret_key))
        _raise_for_account_error(response)
        _raise_for_status(response)
        return uuid.UUID(str(response.json()["id"]))

    def admin_is_confirmed(self, user_id: uuid.UUID) -> bool:
        """Whether the user's email is confirmed, i.e. they accepted their invite."""
        response = self._request("GET", f"/admin/users/{user_id}", key_headers(self._secret_key))
        if response.status_code == 404:
            raise UserNotFoundError("User not found", status=404, code=_error_code(response))
        _raise_for_status(response)
        return bool(response.json().get("email_confirmed_at"))

    def admin_set_password(self, user_id: uuid.UUID, password: str) -> None:
        response = self._request(
            "PUT",
            f"/admin/users/{user_id}",
            key_headers(self._secret_key),
            {"password": password},
        )
        _raise_for_account_error(response)
        _raise_for_status(response)

    def admin_generate_link(self, link_type: LinkType, email: str) -> str:
        """Create a single-use invite or recovery token for `email` and return its hash.

        Supabase sends nothing: the app emails a link to its own pages, which redeem the
        hash with `verify_link`. Each new token replaces the user's previous one. An invite
        for an existing, still unconfirmed user reuses that user.
        """
        response = self._post(
            "/admin/generate_link",
            {"type": link_type, "email": email},
            key_headers(self._secret_key),
        )
        if response.status_code == 404:
            raise UserNotFoundError("User not found", status=404, code=_error_code(response))
        _raise_for_account_error(response)
        _raise_for_status(response)
        return str(response.json()["hashed_token"])

    def verify_link(self, link_type: LinkType, token_hash: str) -> AuthSession:
        """Redeem a token from `admin_generate_link` and return a session for its user."""
        response = self._post(
            "/verify",
            {"type": link_type, "token_hash": token_hash},
            key_headers(self._publishable_key),
        )
        if response.status_code in (400, 401, 403, 404):
            raise InvalidLinkError(
                "Link is invalid or has expired", status=401, code=_error_code(response)
            )
        return self._session(response)

    def admin_delete_user(self, user_id: uuid.UUID) -> None:
        try:
            response = self._client.delete(
                f"{self._auth_url}/admin/users/{user_id}", headers=key_headers(self._secret_key)
            )
            _raise_for_status(response)
        except (httpx.HTTPError, SupabaseAuthError):
            logger.warning("Could not delete Supabase user %s", user_id, exc_info=True)

    def _post(self, path: str, body: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        return self._request("POST", path, headers, body)

    def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        try:
            return self._client.request(
                method, f"{self._auth_url}{path}", json=body, headers=headers
            )
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


def _raise_for_account_error(response: httpx.Response) -> None:
    if response.status_code not in (400, 422):
        return
    code = _error_code(response)
    if code == "email_exists" or "already" in response.text.lower():
        raise EmailTakenError("Email already registered", status=409, code=code)
    if code == "weak_password":
        raise WeakPasswordError("Password is too weak", status=422, code=code)


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
