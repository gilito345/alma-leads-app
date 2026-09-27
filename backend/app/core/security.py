"""Verification of Supabase Auth access tokens.

Supabase signs user access tokens with an asymmetric key (ES256/RS256) published at
`/auth/v1/.well-known/jwks.json`; older projects sign with a shared HS256 secret. Both are
accepted. A valid token only proves *who* the caller is; whether they are an attorney is
decided by the `users` table (see app.api.deps.get_current_user).
"""

import logging
import uuid
from typing import Any, Protocol

import jwt

from app.core.config import Settings

logger = logging.getLogger(__name__)

AUDIENCE = "authenticated"
_ASYMMETRIC_ALGORITHMS = ("ES256", "RS256")


class SigningKeySource(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class TokenVerifier:
    def __init__(self, settings: Settings, *, jwks: SigningKeySource | None = None) -> None:
        self._hs256_secret = (
            settings.supabase_jwt_secret.get_secret_value()
            if settings.supabase_jwt_secret
            else None
        )
        self._jwks = jwks or jwt.PyJWKClient(
            f"{settings.supabase_api_url}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=600,
            headers={"apikey": settings.supabase_publishable_key.get_secret_value()},
            timeout=5,
        )

    def user_id(self, token: str) -> uuid.UUID | None:
        """The Supabase user id (`sub`) of a valid access token, or None."""
        try:
            algorithm = jwt.get_unverified_header(token).get("alg")
            if algorithm == "HS256":
                if self._hs256_secret is None:
                    return None
                key: Any = self._hs256_secret
            elif algorithm in _ASYMMETRIC_ALGORITHMS:
                key = self._jwks.get_signing_key_from_jwt(token).key
            else:
                return None
            payload = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=AUDIENCE,
                options={"require": ["sub", "exp", "aud"]},
            )
        except jwt.PyJWKClientError:
            logger.warning("Could not fetch Supabase signing keys", exc_info=True)
            return None
        except jwt.PyJWTError:
            return None

        try:
            return uuid.UUID(str(payload["sub"]))
        except ValueError:
            return None
