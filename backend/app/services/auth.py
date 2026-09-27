import hmac
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AuthenticationError, ConflictError, ForbiddenError, InvalidInputError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import SignupStatus
from app.repositories.users import UserRepository


# Arbitrary constant: serializes sign-ups so two "first" accounts can't race past the check.
_SIGNUP_LOCK_KEY = 72_017_001


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

    def signup_status(self) -> SignupStatus:
        code_configured = self.settings.attorney_signup_code is not None
        first_account = self.users.count() == 0
        return SignupStatus(
            open=first_account,
            invite_code_required=not first_account and code_configured,
            enabled=first_account or code_configured,
        )

    def signup(
        self, email: str, full_name: str, password: str, invite_code: str | None
    ) -> tuple[str, int]:
        """Self-service attorney sign-up. Returns an access token for the new account.

        The first account needs no code (bootstrapping a fresh install). After that, the
        caller must present ATTORNEY_SIGNUP_CODE; without one configured, sign-up is closed.
        """
        self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _SIGNUP_LOCK_KEY})
        if self.users.count() > 0:
            expected = self.settings.attorney_signup_code
            if expected is None:
                self.db.rollback()
                raise ForbiddenError(
                    "Sign-up is closed. Ask an existing attorney to create your account.",
                    code="signup_closed",
                )
            if not invite_code or not hmac.compare_digest(
                invite_code.strip().encode(), expected.get_secret_value().encode()
            ):
                self.db.rollback()
                raise ForbiddenError(
                    "That invite code isn't valid.",
                    code="invalid_invite_code",
                    details=[{"field": "invite_code", "message": "Invalid invite code"}],
                )
        try:
            user = self.create_user(email, full_name, password)
        except ValueError as exc:
            raise InvalidInputError(
                str(exc), details=[{"field": "password", "message": str(exc)}]
            ) from exc
        return create_access_token(str(user.id), self.settings)

    def create_user(self, email: str, full_name: str, password: str) -> User:
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        normalized = email.strip().lower()
        if self.users.get_by_email(normalized) is not None:
            self.db.rollback()
            raise ConflictError(
                f"An account with email {normalized} already exists",
                code="email_taken",
                details=[{"field": "email", "message": "This email already has an account"}],
            )
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
