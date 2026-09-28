import logging
from datetime import UTC, datetime, timedelta

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
from app.models import EmailKind, EmailOutbox, User
from app.repositories.users import UserRepository
from app.schemas.auth import InviteResponse
from app.services.supabase_auth import (
    AuthSession,
    EmailTakenError,
    InvalidCredentialsError,
    InvalidLinkError,
    InvalidRefreshTokenError,
    LinkType,
    SupabaseAuth,
    SupabaseAuthError,
    WeakPasswordError,
)

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 12
# At most one reset email per account in this window, however many IPs ask for it.
PASSWORD_RESET_COOLDOWN = timedelta(minutes=1)


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
    Nobody can sign themselves up: accounts come from an invite sent by a signed-in attorney,
    or from the CLI (how the first account is made).
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

    # --- invites --------------------------------------------------------------------------

    def invite(self, email: str, full_name: str, invited_by: User) -> InviteResponse:
        """Create an attorney account without a password and email them a link to set one.

        Inviting someone whose invite is still pending sends a fresh link (the old one stops
        working). Inviting someone who already accepted is a conflict.
        """
        normalized = email.strip().lower()
        name = full_name.strip()
        existing = self.users.get_by_email(normalized)

        created_in_supabase = False
        if existing is not None:
            if not existing.is_active or self._has_accepted(existing):
                raise _email_taken(normalized)
            user = existing
        else:
            try:
                user_id = self.supabase.admin_create_user(normalized, None, name)
            except EmailTakenError as exc:
                # A Supabase identity with no attorney record (e.g. made in Studio).
                raise _email_taken(normalized) from exc
            except SupabaseAuthError as exc:
                raise _upstream(exc) from exc
            created_in_supabase = True
            user = User(id=user_id, email=normalized, full_name=name, is_active=True)
            self.users.add(user)

        try:
            self.db.flush()  # the outbox row references the user
            self._queue_email(EmailKind.ATTORNEY_INVITE, user)
            self.db.commit()
        except Exception:
            self.db.rollback()
            if created_in_supabase:
                # Don't leave a Supabase identity behind without its attorney record.
                self.supabase.admin_delete_user(user.id)
            raise

        logger.info(
            "Attorney invite queued user=%s invited_by=%s resent=%s",
            user.id,
            invited_by.id,
            existing is not None,
        )
        return InviteResponse(
            email=user.email, full_name=user.full_name, resent=existing is not None
        )

    def accept_invite(self, token: str, password: str) -> AuthSession:
        return self._redeem_link("invite", token, password)

    def _has_accepted(self, user: User) -> bool:
        try:
            return self.supabase.admin_is_confirmed(user.id)
        except SupabaseAuthError as exc:
            raise _upstream(exc) from exc

    # --- password reset -------------------------------------------------------------------

    def request_password_reset(self, email: str) -> None:
        """Queue a reset email if `email` belongs to an active attorney; otherwise do nothing.

        The caller gets the same answer either way, so this can't be used to find accounts.
        """
        user = self.users.get_by_email(email.strip().lower())
        if user is None or not user.is_active:
            return
        since = datetime.now(UTC) - PASSWORD_RESET_COOLDOWN
        if self.users.has_recent_email(user.id, EmailKind.PASSWORD_RESET, since):
            return
        self._queue_email(EmailKind.PASSWORD_RESET, user)
        self.db.commit()
        logger.info("Password reset email queued user=%s", user.id)

    def reset_password(self, token: str, password: str) -> AuthSession:
        session = self._redeem_link("recovery", token, password)
        # Anyone who was signed in with the old password is signed out.
        self.supabase.sign_out(session.access_token, scope="others")
        return session

    # --- links ----------------------------------------------------------------------------

    def _redeem_link(self, link_type: LinkType, token: str, password: str) -> AuthSession:
        """Redeem an emailed link, set the account's password and return a signed-in session.

        The password is checked first: redeeming burns the link, so a password Supabase would
        reject must not get that far.
        """
        _check_password(password)
        try:
            session = self.supabase.verify_link(link_type, token.strip())
        except InvalidLinkError as exc:
            raise AuthenticationError(
                "This link is invalid, already used or expired", code="invalid_link"
            ) from exc
        except SupabaseAuthError as exc:
            raise _upstream(exc) from exc

        user = self.users.get(session.user_id)
        if user is None or not user.is_active:
            self.supabase.sign_out(session.access_token)
            raise AuthenticationError(
                "This link is invalid, already used or expired", code="invalid_link"
            )

        try:
            self.supabase.admin_set_password(user.id, password)
        except WeakPasswordError as exc:
            self.supabase.sign_out(session.access_token)
            raise InvalidInputError(
                "Password is too weak",
                details=[{"field": "password", "message": "Too weak"}],
            ) from exc
        except SupabaseAuthError as exc:
            self.supabase.sign_out(session.access_token)
            raise _upstream(exc) from exc
        logger.info("Password set via %s link user=%s", link_type, user.id)
        return session

    def _queue_email(self, kind: EmailKind, user: User) -> None:
        self.db.add(EmailOutbox(user_id=user.id, kind=kind, recipient=user.email))

    # --- CLI ------------------------------------------------------------------------------

    def create_user(self, email: str, full_name: str, password: str) -> User:
        """Create a ready-to-use account with a password. Used by the CLI, which is how the
        first attorney is made; everyone after that is invited from the dashboard."""
        try:
            _check_password(password)
        except InvalidInputError:
            self.db.rollback()
            raise
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


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidInputError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
            details=[{"field": "password", "message": "Too short"}],
        )


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
