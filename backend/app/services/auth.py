import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.users = UserRepository(db)

    def login(self, email: str, password: str) -> tuple[str, int]:
        user = self.users.get_by_email(email)
        # Always verify (against a dummy hash if needed) so timing doesn't reveal accounts.
        valid = verify_password(password, user.hashed_password if user else None)
        if user is None or not valid or not user.is_active:
            raise AuthenticationError("Invalid email or password", code="invalid_credentials")
        return create_access_token(str(user.id), self.settings)

    def user_from_token(self, token: str) -> User:
        subject = decode_access_token(token, self.settings)
        if subject is None:
            raise AuthenticationError("Invalid or expired token")
        try:
            user_id = uuid.UUID(subject)
        except ValueError as exc:
            raise AuthenticationError("Invalid or expired token") from exc
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid or expired token")
        return user

    def create_user(self, email: str, full_name: str, password: str) -> User:
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        normalized = email.strip().lower()
        if self.users.get_by_email(normalized) is not None:
            raise ConflictError(f"A user with email {normalized} already exists")
        user = User(
            email=normalized,
            full_name=full_name.strip(),
            hashed_password=hash_password(password),
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
