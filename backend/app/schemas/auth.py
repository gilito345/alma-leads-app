from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """A Supabase Auth session: short-lived access token plus a refresh token."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=4096)


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    password: str = Field(min_length=12, max_length=256)
    invite_code: str | None = Field(default=None, max_length=256)


class SignupStatus(BaseModel):
    """What the sign-up page should show. `open` means no accounts exist yet."""

    open: bool
    invite_code_required: bool
    enabled: bool
