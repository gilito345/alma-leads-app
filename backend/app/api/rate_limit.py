"""Per-client-IP rate limits for the public endpoints.

Limits are held in process memory, which is right for a single API instance. With several
replicas, point slowapi at Redis (`storage_uri`) so the limits are shared.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.errors import error_body

limiter = Limiter(key_func=get_remote_address)


def create_lead_limit() -> str:
    return get_settings().rate_limit_create_lead


def login_limit() -> str:
    return get_settings().rate_limit_login


async def rate_limit_exceeded_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)  # noqa: S101 - registered only for this type
    return JSONResponse(
        status_code=429,
        content=error_body("rate_limited", "Too many requests. Please try again shortly."),
        headers={"Retry-After": "60"},
    )
