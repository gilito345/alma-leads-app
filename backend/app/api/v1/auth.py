from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_access_token, get_auth_service, get_current_user
from app.api.rate_limit import limiter, login_limit
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    SignupStatus,
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


@router.get("/signup", response_model=SignupStatus, summary="Whether sign-up is available")
def signup_status(auth: AuthService = Depends(get_auth_service)) -> SignupStatus:
    return auth.signup_status()


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an attorney account (first account, or with the invite code)",
)
@limiter.limit(login_limit)
def signup(
    request: Request,
    body: SignupRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    session = auth.signup(body.email, body.full_name, body.password, body.invite_code)
    return _tokens(session)


@router.get("/me", response_model=UserSummary, summary="Current user")
def me(user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(user)
