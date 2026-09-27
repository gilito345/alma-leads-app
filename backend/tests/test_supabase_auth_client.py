import json
import uuid

import httpx
import pytest
import respx

from app.services.supabase_auth import (
    EmailTakenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    SupabaseAuthClient,
    SupabaseAuthError,
    WeakPasswordError,
)

BASE = "http://supabase.test"
USER_ID = uuid.uuid4()
SESSION = {
    "access_token": "access",
    "refresh_token": "refresh",
    "expires_in": 3600,
    "user": {"id": str(USER_ID)},
}


@pytest.fixture
def client() -> SupabaseAuthClient:
    return SupabaseAuthClient(BASE, "sb_publishable_x", "sb_secret_y")


@respx.mock
def test_password_sign_in(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/token", params={"grant_type": "password"}).mock(
        return_value=httpx.Response(200, json=SESSION)
    )

    session = client.sign_in_with_password("ada@firm.test", "pw")

    assert session.user_id == USER_ID
    assert session.refresh_token == "refresh"
    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_publishable_x"
    assert "authorization" not in request.headers  # opaque sb_ keys aren't bearer tokens
    assert json.loads(request.content) == {"email": "ada@firm.test", "password": "pw"}


@respx.mock
def test_bad_credentials(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/token").mock(
        return_value=httpx.Response(
            400, json={"code": 400, "error_code": "invalid_credentials", "msg": "Invalid"}
        )
    )
    with pytest.raises(InvalidCredentialsError):
        client.sign_in_with_password("ada@firm.test", "wrong")


@respx.mock
def test_refresh_rejected(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/token", params={"grant_type": "refresh_token"}).mock(
        return_value=httpx.Response(400, json={"error_code": "refresh_token_not_found"})
    )
    with pytest.raises(InvalidRefreshTokenError):
        client.refresh_session("old")


@respx.mock
def test_admin_create_user_uses_secret_key(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/admin/users").mock(
        return_value=httpx.Response(200, json={"id": str(USER_ID)})
    )

    assert client.admin_create_user("ada@firm.test", "pw-long-enough", "Ada") == USER_ID

    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_secret_y"
    body = json.loads(request.content)
    assert body["email_confirm"] is True
    assert body["user_metadata"] == {"full_name": "Ada"}


@pytest.mark.parametrize(
    ("error_code", "expected"),
    [("email_exists", EmailTakenError), ("weak_password", WeakPasswordError)],
)
@respx.mock
def test_admin_create_user_errors(client: SupabaseAuthClient, error_code, expected) -> None:
    respx.post(f"{BASE}/auth/v1/admin/users").mock(
        return_value=httpx.Response(422, json={"code": 422, "error_code": error_code, "msg": "x"})
    )
    with pytest.raises(expected):
        client.admin_create_user("ada@firm.test", "pw", "Ada")


def test_legacy_jwt_keys_are_also_sent_as_bearer() -> None:
    from app.services.supabase_auth import key_headers

    assert key_headers("eyJhbGciOi.legacy.key") == {
        "apikey": "eyJhbGciOi.legacy.key",
        "Authorization": "Bearer eyJhbGciOi.legacy.key",
    }


@respx.mock
def test_unreachable(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/token").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(SupabaseAuthError):
        client.sign_in_with_password("ada@firm.test", "pw")
