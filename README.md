# Leads App

A public lead-intake form and an internal, auth-guarded dashboard for attorneys.

- Prospects submit their first name, last name, email and resume/CV.
- On submission, the prospect gets a confirmation email and an attorney gets a notification.
- Attorneys sign in to see every lead with its details, download resumes, and move a lead
  from `PENDING` to `REACHED_OUT` once they've contacted the prospect.

| Layer | Tech |
|---|---|
| API | FastAPI, SQLAlchemy 2, Alembic |
| Database, auth, file storage | [Supabase](https://supabase.com): Postgres, Supabase Auth, Supabase Storage (run locally with the Supabase CLI) |
| Email | Resend, sent by a background worker from a transactional outbox |
| Web | Next.js 16 (App Router, TypeScript, Tailwind CSS 4) |

The reasoning behind the architecture is in [`docs/DESIGN.md`](docs/DESIGN.md).

## Running locally

**Prerequisites**

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), running
- Git
- The [Supabase CLI](https://supabase.com/docs/guides/local-development/cli/getting-started):
  - **Windows** (PowerShell), via [Scoop](https://scoop.sh):
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser   # once, if Scoop isn't installed
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression        # installs Scoop
    scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
    scoop install supabase
    ```
  - **macOS / Linux:** `brew install supabase/tap/supabase`
  - Or, with Node.js installed, prefix the commands below with `npx` (`npx supabase start`).

**1. Get the code and configure**

```bash
git clone https://github.com/gilito345/alma-leads-app.git
cd alma-leads-app
cp .env.example .env        # PowerShell: copy .env.example .env
```

Edit `.env` and set:

- `RESEND_API_KEY`: your key from [resend.com](https://resend.com/api-keys). Leave it empty to run without sending real email; the worker then logs each email instead (`docker compose logs -f worker`).
- `ATTORNEY_NOTIFICATION_EMAIL`: the inbox that receives new-lead notifications.

You'll fill in the two Supabase keys after the next step.

> **Resend without a verified domain** can only deliver to the email address that owns the Resend account. To demo end to end, use that address both as `ATTORNEY_NOTIFICATION_EMAIL` and in the form. To email anyone, [verify a domain](https://resend.com/domains) and set `EMAIL_FROM` to an address on it.

**2. Start Supabase** (from the repo root)

```bash
supabase start
```

The first run downloads the Supabase images and takes a few minutes. It starts Postgres, Auth, Storage and Studio using [`supabase/config.toml`](supabase/config.toml), which also creates the private `resumes` bucket and turns off public self-sign-up.

When it finishes, it prints an **Authentication Keys** table. Copy the **Publishable** key into `SUPABASE_PUBLISHABLE_KEY` and the **Secret** key into `SUPABASE_SECRET_KEY` in `.env`. (`supabase status` prints them again any time.) The database URL and Supabase URL in `.env.example` already match the local stack.

**3. Start the app**

```bash
docker compose up --build
```

This builds and starts the API (which applies the database migrations on startup), the email worker and the web app.

**4. Create the first attorney account**

There's no public sign-up, so strangers can't create accounts and see leads. Create the first account from the command line (it prompts for a password of at least 12 characters):

```bash
docker compose exec api python -m app.cli create-user --email you@example.com --name "Your Name"
```

Then sign in at http://localhost:3000/login. To add colleagues, use **Invite attorney** in the dashboard header: they get an email with a single-use link to choose their password (it expires after 24 hours; inviting them again sends a fresh one). Forgotten passwords are reset from **Forgot your password?** on the sign-in page. Without a `RESEND_API_KEY`, these emails, links included, appear in `docker compose logs -f worker`.

**5. Try it**

| URL | What |
|---|---|
| http://localhost:3000/apply | Public lead form |
| http://localhost:3000/login | Attorney sign-in, then the dashboard at `/leads` |
| http://localhost:3000/invite | Invite another attorney (signed in) |
| http://localhost:3000/forgot-password | Email yourself a password-reset link |
| http://localhost:8000/docs | Interactive API docs (OpenAPI) |
| http://localhost:54323 | Supabase Studio: browse tables, auth users and uploaded resumes |

Submit the form with a PDF, DOC or DOCX, then watch `docker compose logs -f worker` to see both emails go out. Sign in to see the lead and mark it as reached out.

**Stopping:** `docker compose down`, then `supabase stop`. Data is kept between runs; `supabase stop --no-backup` discards it.

### Using a hosted Supabase project instead

Create a project at [supabase.com](https://supabase.com), then in `.env` set `SUPABASE_URL` to the project URL, `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY` from *Project Settings → API Keys*, and `DATABASE_URL` to the connection string (with the `postgresql+psycopg://` scheme). Create a private bucket named `resumes`. In the project's Auth settings, turn off *Allow new users to sign up* (accounts are only created by the backend: the CLI and invites) but keep the Email provider enabled, since disabling it also blocks password sign-in; set the email OTP expiry to 86400 seconds to match the 24-hour links. Skip `supabase start`.

## Running without Docker (for development)

With `supabase start` running:

**API** (Python 3.12+, [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
export DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres
export SUPABASE_URL=http://127.0.0.1:54321
export SUPABASE_PUBLISHABLE_KEY=...   # from `supabase status`
export SUPABASE_SECRET_KEY=...        # from `supabase status`
export ATTORNEY_NOTIFICATION_EMAIL=you@example.com RESEND_API_KEY=   # empty = log emails
uv run alembic upgrade head
uv run uvicorn --factory app.main:create_app --reload        # API on :8000
uv run python -m app.worker                                  # in another terminal
```

**Web** (Node 20.9+):

```bash
cd frontend
npm install
API_INTERNAL_URL=http://localhost:8000 npm run dev            # web on :3000
```

## Tests and checks

```bash
# Backend: needs a plain Postgres database it may wipe (not your Supabase one).
# Supabase Auth and Storage are replaced by in-memory fakes.
cd backend
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/leads_test uv run pytest
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
supabase/    Supabase CLI config for the local stack (config.toml)
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
| `POST` | `/api/v1/auth/login` | Public; returns a Supabase session |
| `POST` | `/api/v1/auth/refresh` | Public (with a refresh token) |
| `POST` | `/api/v1/auth/logout` | Attorney |
| `POST` | `/api/v1/auth/invites` (`{"email", "full_name"}`) | Attorney |
| `POST` | `/api/v1/auth/invites/accept` (`{"token", "password"}`) | Public (with an invite link's token); returns a session |
| `POST` | `/api/v1/auth/password-reset` (`{"email"}`) | Public; same answer whether or not the account exists |
| `POST` | `/api/v1/auth/password-reset/confirm` (`{"token", "password"}`) | Public (with a reset link's token); returns a session |
| `GET` | `/api/v1/auth/me` | Attorney |
| `GET` | `/healthz` | Public |

Full request and response schemas are at http://localhost:8000/docs.
