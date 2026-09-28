from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_access_token, get_auth_service, get_current_user
from app.api.rate_limit import limiter, login_limit
from app.models import User
from app.schemas.auth import (
    InviteRequest,
    InviteResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetRequest,
    RefreshRequest,
    SetPasswordRequest,
    TokenResponse,
)
from app.schemas.lead import UserSummary
from app.services.auth import AuthService
from app.services.supabase_auth import AuthSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(session: AuthSession) -> TokenResponse:
    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
    )


@router.post("/login", response_model=TokenResponse, summary="Sign in (attorneys)")
@limiter.limit(login_limit)
def login(
    request: Request,
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return _tokens(auth.login(body.email, body.password))


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token")
def refresh(body: RefreshRequest, auth: AuthService = Depends(get_auth_service)) -> TokenResponse:
    return _tokens(auth.refresh(body.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(
    token: str = Depends(get_access_token),
    auth: AuthService = Depends(get_auth_service),
) -> Response:
    auth.logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserSummary, summary="Current user")
def me(user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(user)


@router.post(
    "/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Invite an attorney by email (or re-send a pending invite)",
)
def invite(
    body: InviteRequest,
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> InviteResponse:
    return auth.invite(body.email, body.full_name, invited_by=user)


@router.post(
    "/invites/accept",
    response_model=TokenResponse,
    summary="Accept an invite: set a password and sign in",
)
@limiter.limit(login_limit)
def accept_invite(
    request: Request,
    body: SetPasswordRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return _tokens(auth.accept_invite(body.token, body.password))


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Email a password-reset link (same response whether or not the account exists)",
)
@limiter.limit(login_limit)
def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    auth: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    auth.request_password_reset(body.email)
    return MessageResponse(
        message="If an account exists for that email, a reset link is on its way."
    )


@router.post(
    "/password-reset/confirm",
    response_model=TokenResponse,
    summary="Set a new password from a reset link and sign in",
)
@limiter.limit(login_limit)
def confirm_password_reset(
    request: Request,
    body: SetPasswordRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return _tokens(auth.reset_password(body.token, body.password))
