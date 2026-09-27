# Leads App

A public lead-intake form and an internal, auth-guarded dashboard for attorneys.
Prospects submit their name, email and resume; the prospect and an attorney are
emailed; attorneys review leads and mark them `REACHED_OUT`.

- **API:** FastAPI, PostgreSQL, S3-compatible storage (MinIO locally), Resend for email
- **Web:** Next.js (App Router, TypeScript, Tailwind)

See [`docs/DESIGN.md`](docs/DESIGN.md) for the architecture and the reasoning behind it.

> **Status:** design and repo scaffolding. The backend and frontend are being built next;
> full run instructions will be completed alongside them.

## Running locally (planned)

Prerequisites: Docker Desktop, Git.

```bash
cp .env.example .env              # then fill in RESEND_API_KEY and ATTORNEY_NOTIFICATION_EMAIL
docker compose up --build
docker compose exec api python -m app.cli create-user --email you@example.com --name "Your Name"
```

| URL | What |
|---|---|
| http://localhost:3000/apply | Public lead form |
| http://localhost:3000/login | Attorney login → dashboard |
| http://localhost:8000/docs | API docs (OpenAPI) |
| http://localhost:9001 | MinIO console (resumes) |
