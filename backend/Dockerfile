# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app

# Install dependencies first so code changes don't invalidate this layer.
FROM base AS deps
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

FROM base AS runtime
RUN useradd --create-home --uid 10001 app
COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app . .
USER app
EXPOSE 8000
# --proxy-headers lets rate limiting see the real client IP forwarded by the web tier.
# Only trust X-Forwarded-For from addresses in FORWARDED_ALLOW_IPS (set in compose).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 --proxy-headers"]
