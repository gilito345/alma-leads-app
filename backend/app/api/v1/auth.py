from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_auth_service, get_current_user
from app.api.rate_limit import limiter, login_limit
from app.models import User
from app.schemas.auth import LoginRequest, SignupRequest, SignupStatus, TokenResponse
from app.schemas.lead import UserSummary
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Sign in (attorneys)")
@limiter.limit(login_limit)
def login(
    request: Request,
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    token, expires_in = auth.login(body.email, body.password)
    return TokenResponse(access_token=token, expires_in=expires_in)


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
    token, expires_in = auth.signup(body.email, body.full_name, body.password, body.invite_code)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserSummary, summary="Current user")
def me(user: User = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(user)
