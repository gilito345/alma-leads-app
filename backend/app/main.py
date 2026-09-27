import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.concurrency import run_in_threadpool

from app.api.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.v1 import api_router
from app.api.v1.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware
from app.core.security import TokenVerifier
from app.services.storage import ObjectStorage, build_storage
from app.services.supabase_auth import SupabaseAuth, SupabaseAuthClient

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    storage: ObjectStorage | None = None,
    supabase_auth: SupabaseAuth | None = None,
    token_verifier: TokenVerifier | None = None,
) -> FastAPI:
    """Build the API. Run with `uvicorn --factory app.main:create_app`."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.storage_auto_create_bucket:
            try:
                await run_in_threadpool(app.state.storage.ensure_bucket)
            except Exception:
                # Don't take the whole API down; uploads will report the problem instead.
                logger.exception("Could not verify or create the resume storage bucket")
        yield

    app = FastAPI(
        title="Leads API",
        version="0.1.0",
        description="Public lead intake and internal lead management.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.storage = storage or build_storage(settings)
    app.state.supabase_auth = supabase_auth or SupabaseAuthClient.from_settings(settings)
    app.state.token_verifier = token_verifier or TokenVerifier(settings)

    limiter.enabled = settings.rate_limit_enabled
    app.state.limiter = limiter

    register_exception_handlers(app)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(health_router)
    return app
