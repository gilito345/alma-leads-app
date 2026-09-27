# Leads App

A public lead-intake form and an internal, auth-guarded dashboard for attorneys.

- Prospects submit their first name, last name, email and resume/CV.
- On submission, the prospect gets a confirmation email and an attorney gets a notification.
- Attorneys sign in to see every lead with its details, download resumes, and move a lead
  from `PENDING` to `REACHED_OUT` once they've contacted the prospect.

| Layer | Tech |
|---|---|
| API | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL |
| File storage | Local Docker volume in development, S3 in production (same interface) |
| Email | Resend, sent by a background worker from a transactional outbox |
| Web | Next.js 16 (App Router, TypeScript, Tailwind CSS 4) |

The reasoning behind the architecture is in [`docs/DESIGN.md`](docs/DESIGN.md).

## Running locally with Docker (recommended)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with Compose v2) and Git.

1. **Configure**

   ```bash
   git clone https://github.com/gilito345/alma-leads-app.git
   cd alma-leads-app
   cp .env.example .env
   ```

   Edit `.env`:

   - `RESEND_API_KEY`: your key from [resend.com](https://resend.com/api-keys). Leave it empty to run without sending real email; the worker then logs each email instead (`docker compose logs -f worker`).
   - `ATTORNEY_NOTIFICATION_EMAIL`: the inbox that receives new-lead notifications.

   > **Resend without a verified domain** can only deliver to the email address that owns the Resend account. To demo end to end, use that address both as `ATTORNEY_NOTIFICATION_EMAIL` and in the form. To email anyone, [verify a domain](https://resend.com/domains) and set `EMAIL_FROM` to an address on it.

2. **Start everything**

   ```bash
   docker compose up --build
   ```

   This starts Postgres, the API (which runs database migrations on startup), the email worker and the web app. The first build takes a few minutes.

3. **Create an attorney account** (in a second terminal)

   ```bash
   docker compose exec api python -m app.cli create-user --email you@example.com --name "Your Name"
   ```

   You'll be prompted for a password (at least 12 characters).

4. **Try it**

   | URL | What |
   |---|---|
   | http://localhost:3000/apply | Public lead form |
   | http://localhost:3000/login | Attorney sign-in, then the dashboard at `/leads` |
   | http://localhost:8000/docs | Interactive API docs (OpenAPI) |

   Submit the form with a PDF, DOC or DOCX, then watch `docker compose logs -f worker` to see both emails go out. Sign in to see the lead and mark it as reached out.

To stop: `docker compose down` (add `-v` to also delete the database and uploaded resumes).

**Using S3 instead of local files:** set `STORAGE_BACKEND=s3` plus `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` in `.env` (and `S3_ENDPOINT_URL` for S3-compatible services such as Cloudflare R2). The bucket is created on startup if it doesn't exist.

## Running without Docker (for development)

You'll still need Postgres. The simplest is to run just that in Docker, after adding `ports: ["5432:5432"]` under `db` in `docker-compose.yml`:

```bash
docker compose up -d db
```

Resumes are written to `backend/storage/resumes` by default.

**API** (Python 3.12+, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
export DATABASE_URL=postgresql+psycopg://leads:leads@localhost:5432/leads
export JWT_SECRET=local-dev-only-secret-change-me-before-deploying
export ATTORNEY_NOTIFICATION_EMAIL=you@example.com RESEND_API_KEY=   # empty = log emails
uv run alembic upgrade head
uv run uvicorn --factory app.main:create_app --reload        # API on :8000
uv run python -m app.worker                                  # in another terminal
uv run python -m app.cli create-user --email you@example.com --name "You"
```

**Web** (Node 20.9+):

```bash
cd frontend
npm install
API_INTERNAL_URL=http://localhost:8000 npm run dev            # web on :3000
```

## Tests and checks

```bash
# Backend: needs a Postgres database it may wipe
cd backend
TEST_DATABASE_URL=postgresql+psycopg://leads:leads@localhost:5432/leads_test uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy app

# Frontend
cd frontend
npm run lint && npm test && npm run build
```

CI runs all of these on every push and pull request (`.github/workflows/ci.yml`).

## Project layout

```
backend/     FastAPI app (app/), Alembic migrations, tests
frontend/    Next.js app (src/app routes, src/components, src/lib)
docs/        Design document
docker-compose.yml, .env.example
```

## API overview

| Method | Path | Auth |
|---|---|---|
| `POST` | `/api/v1/leads` | Public (multipart: `first_name`, `last_name`, `email`, `resume`) |
| `GET` | `/api/v1/leads?state=&page=&page_size=` | Attorney |
| `GET` | `/api/v1/leads/{id}` | Attorney |
| `PATCH` | `/api/v1/leads/{id}` (`{"state": "REACHED_OUT"}`) | Attorney |
| `GET` | `/api/v1/leads/{id}/resume` | Attorney |
| `POST` | `/api/v1/auth/login` | Public |
| `GET` | `/api/v1/auth/me` | Attorney |
| `GET` | `/healthz` | Public |

Full request and response schemas are at http://localhost:8000/docs.
