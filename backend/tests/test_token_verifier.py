import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import Settings
from app.core.security import TokenVerifier
from tests.fakes import NoJwks, make_access_token


class StaticJwks:
    def __init__(self, public_key: object) -> None:
        self.public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> object:
        return SimpleNamespace(key=self.public_key)


def es256_token(private_key: ec.EllipticCurvePrivateKey, user_id: uuid.UUID, **claims) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "test"})


def test_accepts_es256_tokens_from_jwks(settings: Settings) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(settings, jwks=StaticJwks(key.public_key()))
    user_id = uuid.uuid4()

    assert verifier.user_id(es256_token(key, user_id)) == user_id


def test_rejects_es256_token_signed_by_another_key(settings: Settings) -> None:
    trusted = ec.generate_private_key(ec.SECP256R1())
    attacker = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(settings, jwks=StaticJwks(trusted.public_key()))

    assert verifier.user_id(es256_token(attacker, uuid.uuid4())) is None


def test_accepts_hs256_with_configured_secret(settings: Settings) -> None:
    user_id = uuid.uuid4()
    assert TokenVerifier(settings, jwks=NoJwks()).user_id(make_access_token(user_id)) == user_id


def test_rejects_hs256_when_no_secret_configured(settings: Settings) -> None:
    without_secret = settings.model_copy(update={"supabase_jwt_secret": None})
    verifier = TokenVerifier(without_secret, jwks=NoJwks())
    assert verifier.user_id(make_access_token(uuid.uuid4())) is None


def test_rejects_unsigned_and_garbage_tokens(settings: Settings) -> None:
    verifier = TokenVerifier(settings, jwks=NoJwks())
    unsigned = jwt.encode(
        {"sub": str(uuid.uuid4()), "aud": "authenticated", "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    assert verifier.user_id(unsigned) is None
    assert verifier.user_id("not-a-token") is None


def test_jwks_outage_fails_closed(settings: Settings) -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(settings, jwks=NoJwks())  # NoJwks raises PyJWKClientError
    assert verifier.user_id(es256_token(key, uuid.uuid4())) is None
