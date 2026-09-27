from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.core.security import TokenVerifier
from app.db.session import get_db
from app.models import User
from app.services.auth import AuthService
from app.services.leads import LeadService
from app.services.storage import ObjectStorage
from app.services.supabase_auth import SupabaseAuth

_bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_storage(request: Request) -> ObjectStorage:
    storage: ObjectStorage = request.app.state.storage
    return storage


def get_supabase_auth(request: Request) -> SupabaseAuth:
    supabase: SupabaseAuth = request.app.state.supabase_auth
    return supabase


def get_token_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier = request.app.state.token_verifier
    return verifier


def get_lead_service(
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_app_settings),
) -> LeadService:
    return LeadService(db, storage, settings)


def get_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    supabase: SupabaseAuth = Depends(get_supabase_auth),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> AuthService:
    return AuthService(db, settings, supabase, verifier)


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated")
    return credentials.credentials


def get_current_user(
    token: str = Depends(get_access_token),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    """The signed-in attorney: a valid Supabase access token *and* an active attorney record."""
    return auth.user_from_token(token)
