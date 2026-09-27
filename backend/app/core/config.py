from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables (and `.env` if present).

    Missing required values fail fast at startup rather than at first use.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"

    # Database
    database_url: str

    # Resume storage: "local" (files on disk, for development) or "s3" (production)
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./storage/resumes"

    # S3 (used when storage_backend=s3)
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_bucket: str = "resumes"
    s3_region: str = "us-east-1"
    s3_auto_create_bucket: bool = True

    # Auth
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480

    # Email
    resend_api_key: SecretStr | None = None
    email_from: str = "Leads <onboarding@resend.dev>"
    attorney_notification_email: EmailStr
    email_max_attempts: int = 5
    worker_poll_interval_seconds: float = 5.0
    worker_batch_size: int = 10

    # Web
    web_origin: str = "http://localhost:3000"

    # Public form limits
    max_resume_bytes: int = 10 * 1024 * 1024
    rate_limit_enabled: bool = True
    rate_limit_create_lead: str = "5/minute"
    rate_limit_login: str = "10/minute"

    @field_validator(
        "s3_endpoint_url", "s3_access_key_id", "s3_secret_access_key", "resend_api_key", mode="before"
    )
    @classmethod
    def _empty_as_none(cls, value: object) -> object:
        # `KEY=` in an env file means "not set", not "set to an empty string".
        return None if value == "" else value

    @property
    def max_request_body_bytes(self) -> int:
        # Resume plus room for the other form fields and multipart framing.
        return self.max_resume_bytes + 64 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
