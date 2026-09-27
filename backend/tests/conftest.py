"""Test fixtures.

Tests run against a real PostgreSQL database (FOR UPDATE SKIP LOCKED, enums and timestamps
behave differently on SQLite). Point TEST_DATABASE_URL at a disposable database; its schema
is dropped and rebuilt from the Alembic migrations at the start of the run.
"""

import os
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/leads_test"
)
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "DATABASE_URL": os.environ["TEST_DATABASE_URL"],
        "SUPABASE_URL": "http://supabase.test",
        "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
        "SUPABASE_SECRET_KEY": "sb_secret_test",
        "SUPABASE_JWT_SECRET": "test-supabase-jwt-secret-long-enough-for-hs256",
        "ATTORNEY_NOTIFICATION_EMAIL": "intake@firm.test",
        "WEB_ORIGIN": "http://web.test",
        "RATE_LIMIT_ENABLED": "false",
        "STORAGE_AUTO_CREATE_BUCKET": "false",
        "STORAGE_BACKEND": "local",
        "RESEND_API_KEY": "",
    }
)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.security import TokenVerifier  # noqa: E402
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402
from app.services.auth import AuthService  # noqa: E402
from app.services.storage import InMemoryObjectStorage  # noqa: E402
from tests.fakes import FakeSupabaseAuth, NoJwks  # noqa: E402
from tests.helpers import ATTORNEY_PASSWORD  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> Iterator[None]:
    with get_engine().begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield
    get_engine().dispose()


@pytest.fixture(autouse=True)
def _clean_tables() -> Iterator[None]:
    yield
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE email_outbox, leads, users RESTART IDENTITY CASCADE"))


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def storage() -> InMemoryObjectStorage:
    return InMemoryObjectStorage()


@pytest.fixture
def supabase_auth() -> FakeSupabaseAuth:
    return FakeSupabaseAuth()


@pytest.fixture
def token_verifier(settings: Settings) -> TokenVerifier:
    return TokenVerifier(settings, jwks=NoJwks())


@pytest.fixture
def auth_service(
    db: Session,
    settings: Settings,
    supabase_auth: FakeSupabaseAuth,
    token_verifier: TokenVerifier,
) -> AuthService:
    return AuthService(db, settings, supabase_auth, token_verifier)


@pytest.fixture
def app(
    settings: Settings,
    storage: InMemoryObjectStorage,
    supabase_auth: FakeSupabaseAuth,
    token_verifier: TokenVerifier,
) -> FastAPI:
    return create_app(
        settings, storage=storage, supabase_auth=supabase_auth, token_verifier=token_verifier
    )


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def attorney(auth_service: AuthService) -> User:
    return auth_service.create_user("jane@firm.test", "Jane Attorney", ATTORNEY_PASSWORD)


@pytest.fixture
def auth_headers(client: TestClient, attorney: User) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": attorney.email, "password": ATTORNEY_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
