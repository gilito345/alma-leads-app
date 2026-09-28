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


class InviteRequest(BaseModel):
    email: EmailStr
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]


class InviteResponse(BaseModel):
    email: str
    full_name: str
    resent: bool = Field(description="True if this re-sent a pending invite")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class SetPasswordRequest(BaseModel):
    """Redeem an invite or password-reset link by choosing a password."""

    token: str = Field(min_length=1, max_length=512)
    password: str = Field(min_length=12, max_length=256)
