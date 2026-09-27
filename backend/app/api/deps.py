from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.db.session import get_db
from app.models import User
from app.services.auth import AuthService
from app.services.leads import LeadService
from app.services.storage import ObjectStorage

_bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_storage(request: Request) -> ObjectStorage:
    storage: ObjectStorage = request.app.state.storage
    return storage


def get_lead_service(
    db: Session = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
    settings: Settings = Depends(get_app_settings),
) -> LeadService:
    return LeadService(db, storage, settings)


def get_auth_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> AuthService:
    return AuthService(db, settings)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated")
    return auth.user_from_token(credentials.credentials)
