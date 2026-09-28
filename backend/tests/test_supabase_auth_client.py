import json
import uuid

import httpx
import pytest
import respx

from app.services.supabase_auth import (
    EmailTakenError,
    InvalidCredentialsError,
    InvalidLinkError,
    InvalidRefreshTokenError,
    SupabaseAuthClient,
    SupabaseAuthError,
    UserNotFoundError,
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


@respx.mock
def test_create_user_without_password_leaves_it_unconfirmed(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/admin/users").mock(
        return_value=httpx.Response(200, json={"id": str(USER_ID)})
    )

    assert client.admin_create_user("new@firm.test", None, "New") == USER_ID

    body = json.loads(route.calls.last.request.content)
    assert body == {"email": "new@firm.test", "user_metadata": {"full_name": "New"}}


@respx.mock
def test_generate_link_returns_the_token_hash(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/admin/generate_link").mock(
        return_value=httpx.Response(
            200, json={"id": str(USER_ID), "hashed_token": "abc123", "action_link": "x"}
        )
    )

    assert client.admin_generate_link("invite", "new@firm.test") == "abc123"

    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_secret_y"
    assert json.loads(request.content) == {"type": "invite", "email": "new@firm.test"}


@respx.mock
def test_generate_invite_for_accepted_user_is_email_taken(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/admin/generate_link").mock(
        return_value=httpx.Response(422, json={"code": 422, "error_code": "email_exists"})
    )
    with pytest.raises(EmailTakenError):
        client.admin_generate_link("invite", "jane@firm.test")


@respx.mock
def test_generate_recovery_for_unknown_user(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/admin/generate_link").mock(
        return_value=httpx.Response(404, json={"code": 404, "error_code": "user_not_found"})
    )
    with pytest.raises(UserNotFoundError):
        client.admin_generate_link("recovery", "nobody@firm.test")


@respx.mock
def test_verify_link_returns_a_session(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/verify").mock(
        return_value=httpx.Response(200, json=SESSION)
    )

    session = client.verify_link("recovery", "abc123")

    assert session.user_id == USER_ID
    request = route.calls.last.request
    assert request.headers["apikey"] == "sb_publishable_x"
    assert json.loads(request.content) == {"type": "recovery", "token_hash": "abc123"}


@respx.mock
def test_used_or_expired_link(client: SupabaseAuthClient) -> None:
    respx.post(f"{BASE}/auth/v1/verify").mock(
        return_value=httpx.Response(403, json={"code": 403, "error_code": "otp_expired"})
    )
    with pytest.raises(InvalidLinkError):
        client.verify_link("invite", "abc123")


@respx.mock
def test_is_confirmed(client: SupabaseAuthClient) -> None:
    route = respx.get(f"{BASE}/auth/v1/admin/users/{USER_ID}")
    route.mock(return_value=httpx.Response(200, json={"email_confirmed_at": None}))
    assert client.admin_is_confirmed(USER_ID) is False
    route.mock(return_value=httpx.Response(200, json={"email_confirmed_at": "2026-09-27T00:00Z"}))
    assert client.admin_is_confirmed(USER_ID) is True


@respx.mock
def test_set_password_rejects_weak_passwords(client: SupabaseAuthClient) -> None:
    route = respx.put(f"{BASE}/auth/v1/admin/users/{USER_ID}").mock(
        return_value=httpx.Response(422, json={"code": 422, "error_code": "weak_password"})
    )
    with pytest.raises(WeakPasswordError):
        client.admin_set_password(USER_ID, "password1234")
    assert json.loads(route.calls.last.request.content) == {"password": "password1234"}


@respx.mock
def test_sign_out_other_sessions(client: SupabaseAuthClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/logout", params={"scope": "others"}).mock(
        return_value=httpx.Response(204)
    )
    client.sign_out("access", scope="others")
    assert route.called
