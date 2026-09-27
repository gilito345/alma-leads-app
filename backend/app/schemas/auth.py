from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


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
