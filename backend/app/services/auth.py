import hmac
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    InvalidInputError,
)
from app.core.security import TokenVerifier
from app.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import SignupStatus
from app.services.supabase_auth import (
    AuthSession,
    EmailTakenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    SupabaseAuth,
    SupabaseAuthError,
    WeakPasswordError,
)

logger = logging.getLogger(__name__)

# Arbitrary constant: serializes sign-ups so two "first" accounts can't race past the check.
_SIGNUP_LOCK_KEY = 72_017_001
MIN_PASSWORD_LENGTH = 12


class UpstreamAuthError(AppError):
    status_code = 502
    code = "auth_unavailable"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"


class AuthService:
    """Attorney accounts on top of Supabase Auth.

    Supabase Auth owns identities, passwords and sessions. The `users` table records which
    Supabase users are attorneys (and their display names); only they can use the dashboard.
    """

    def __init__(
        self,
        db: Session,
        settings: Settings,
        supabase: SupabaseAuth,
        verifier: TokenVerifier,
    ) -> None:
        self.db = db
        self.settings = settings
        self.supabase = supabase
        self.verifier = verifier
        self.users = UserRepository(db)

    # --- sessions -------------------------------------------------------------------------

    def login(self, email: str, password: str) -> AuthSession:
        try:
            session = self.supabase.sign_in_with_password(email.strip().lower(), password)
        except InvalidCredentialsError as exc:
            raise AuthenticationError(
                "Invalid email or password", code="invalid_credentials"
            ) from exc
        except SupabaseAuthError as exc:
            raise _upstream(exc) from exc

        user = self.users.get(session.user_id)
        if user is None or not user.is_active:
            # A Supabase identity that isn't (or is no longer) an attorney. Same message as a
            # wrong password, so the endpoint doesn't reveal which accounts exist.
            self.supabase.sign_out(session.access_token)
            raise AuthenticationError("Invalid email or password", code="invalid_credentials")
        return session

    def refresh(self, refresh_token: str) -> AuthSession:
        try:
            session = self.supabase.refresh_session(refresh_token)
        except InvalidRefreshTokenError as exc:
            raise AuthenticationError("Session expired", code="session_expired") from exc
        except SupabaseAuthError as exc:
            raise _upstream(exc) from exc

        user = self.users.get(session.user_id)
        if user is None or not user.is_active:
            self.supabase.sign_out(session.access_token)
            raise AuthenticationError("Session expired", code="session_expired")
        return session

    def logout(self, access_token: str) -> None:
        self.supabase.sign_out(access_token)

    def user_from_token(self, token: str) -> User:
        user_id = self.verifier.user_id(token)
        if user_id is None:
            raise AuthenticationError("Invalid or expired token")
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise ForbiddenError("This account doesn't have access", code="not_an_attorney")
        return user

    # --- sign-up --------------------------------------------------------------------------

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
    ) -> AuthSession:
        """Self-service attorney sign-up; returns a session for the new account.

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

        self.create_user(email, full_name, password)
        return self.login(email, password)

    def create_user(self, email: str, full_name: str, password: str) -> User:
        """Create the Supabase identity and the matching attorney record."""
        if len(password) < MIN_PASSWORD_LENGTH:
            self.db.rollback()
            raise InvalidInputError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
                details=[{"field": "password", "message": "Too short"}],
            )
        normalized = email.strip().lower()
        if self.users.get_by_email(normalized) is not None:
            self.db.rollback()
            raise _email_taken(normalized)

        try:
            user_id = self.supabase.admin_create_user(normalized, password, full_name.strip())
        except EmailTakenError as exc:
            self.db.rollback()
            raise _email_taken(normalized) from exc
        except WeakPasswordError as exc:
            self.db.rollback()
            raise InvalidInputError(
                "Password is too weak",
                details=[{"field": "password", "message": "Too weak"}],
            ) from exc
        except SupabaseAuthError as exc:
            self.db.rollback()
            raise _upstream(exc) from exc

        user = User(id=user_id, email=normalized, full_name=full_name.strip(), is_active=True)
        try:
            self.users.add(user)
            self.db.commit()
        except Exception:
            self.db.rollback()
            # Don't leave a Supabase identity behind without its attorney record.
            self.supabase.admin_delete_user(user_id)
            raise
        self.db.refresh(user)
        logger.info("Attorney account created id=%s", user.id)
        return user


def _email_taken(email: str) -> ConflictError:
    return ConflictError(
        f"An account with email {email} already exists",
        code="email_taken",
        details=[{"field": "email", "message": "This email already has an account"}],
    )


def _upstream(exc: SupabaseAuthError) -> AppError:
    if exc.status == 429:
        return RateLimitedError("Too many attempts. Try again shortly.")
    return UpstreamAuthError("Authentication service unavailable")
