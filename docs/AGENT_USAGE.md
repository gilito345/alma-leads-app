# Coding-Agent Usage

## 1. Writeup

**Tools.** [Claude Code](https://claude.com/claude-code) (Claude Opus 5.5) in two sessions. The first, a cloud session on claude.ai, designed the system and wrote the whole app, pushing to GitHub through the Claude GitHub App. Its sandbox couldn't install packages, so that code was only syntax-checked. The second, in the Claude desktop app on my machine, ran everything for real under Docker. It fixed what broke and added features, using the app's built-in browser to walk through each change and to sample [tryalma.com](https://www.tryalma.com) for the style guide.

**Delegated vs. kept.** The agent wrote all code, tests and docs (see [`NOTES.md`](../NOTES.md)). I kept what needs judgment or accountability: the stack and platform (Supabase for database, auth and storage; Resend for real email), scope (invite-only accounts, the in-page resume viewer, the contact button), security trade-offs (24-hour invite links, `.doc` as download-only), and secrets (the Resend API key went into `.env` by hand, never through the agent). I also owned verification. The first session's code had never executed, so I had the second session run everything for real before building further, and I tested the app myself, sending back anything that behaved or read wrong. I set the working rule of one commit per change, pushed immediately.

**Where it got it wrong.** To block public sign-up, the first session set `enable_signup = false` under `[auth.email]` in `supabase/config.toml`. In the Supabase CLI that disables the whole email provider, so password sign-in broke too. I caught it by using the app as an attorney would: creating the first account ended in "Authentication service unavailable". The API logs showed the account was created but its sign-in was refused (`email_provider_disabled`). The fix blocks sign-up with the right switch (`[auth] enable_signup = false`) and keeps the email provider on. Both behaviours were verified against Supabase and a warning comment added. The same never-executed code hid a second bug: the tests used `.test` addresses that email validation always rejects, so the suite had never passed. Pinning dependencies with lock files and running CI exactly as GitHub does exposed it.

## 2. Prompt log (selected excerpts)

Prompts are quoted exactly as typed (`[...]` marks text trimmed from a long paste). The line under each summarises what the agent did.

### Session 1: design and build (cloud Claude Code session)

> I'm working on building a web app for production, this is the entire instructions I have to go off:
>
> [the assignment brief, pasted in full]
>
> Let's start with a quick tech stack plan so I know what MCPs you'll need access to and what apps I should install

The agent proposed FastAPI, SQLAlchemy/Alembic and Postgres, object storage for resumes, email behind an interface, and Next.js with TypeScript and Tailwind, all under Docker Compose with GitHub Actions. It listed the access and installs it needed, and asked whether to use a local mail catcher or real delivery.

> https://github.com/gilito345/alma-leads-app real email delivery

The agent chose Resend for real delivery and wrote the design doc, README, Compose file and env template.

> github access sorted, push and then start building the backend and frontend

The agent built the full backend and frontend in one pass:
- **Backend:** leads API, auth, storage adapters, a transactional email outbox and worker, a CLI, and a pytest suite.
- **Frontend:** the public form, login, the leads list and detail pages, and session handling.
- **Plus:** Dockerfiles, CI and run docs.

Its sandbox had no package access, so none of this could be run there.

> make sure the webapp is responsive and fits on different viewports properly

The agent checked the public pages from 320 to 1280px wide. It fixed a cramped tablet layout, added a card layout for the leads list on phones, and made long names and emails wrap.

> use supabase since it comes with db and auth

The agent asked what Supabase should take over and where it should run. I chose **database, auth and storage** and **the local Supabase CLI**. The agent then:
- **Data and auth:** moved them to Supabase, with FastAPI staying the only API and the only Supabase client.
- **Tokens:** verified against Supabase's public signing keys.
- **Data API:** kept away from lead data with row-level security and revoked grants.
- **Storage:** stored resumes in a private bucket.

### Session 2: run, harden and extend (Claude Code desktop app)

> Authentication service unavailable when I tried creating an attorney account

The agent traced this to the config bug described above and fixed it. It checked the fix directly against Supabase: password sign-in now accepted, public sign-up still refused.

> build 1 and 2, and disable email/password signup for the internal UI, rely only on auth

*Following a comparison of Supabase Auth features (1 = email invites, 2 = password reset).* The agent checked Supabase's invite, verify and recovery endpoints against the local stack before writing code. It then built invite-only accounts:
- **Emails:** invite and reset emails go through the existing outbox.
- **Links:** the worker creates the one-time link at send time, so no usable link sits in the database.
- **Resets:** sign out the account's other sessions.

It added 20+ tests and walked through both flows in the browser.

> yes commit it and add the lock files

The agent generated `uv.lock` and `package-lock.json` and ran the full CI suite against the pinned versions. That exposed the never-passing test suite, which it fixed.

> https://www.tryalma.com/ make sure you navigate around to various pages for a better sampling

The agent sampled six pages at desktop and phone widths and read the site's own CSS variables. It wrote `docs/STYLE_GUIDE.md`, with Figtree standing in for Alma's licensed Gellix font, and restyled the app.

> Is there better wording than "Free Consultation" where does that even come from

The agent traced the label to the first session's web-app commit and noted it was a pricing promise nothing else backed up. It proposed alternatives; I chose "Talk to an attorney".

> When i hover over the entries in the leads list it gets highlighted, which is good, but it only actually opens the lead when the you click on the name itself, which is unintuitive, it should open regardless where exactly you click on the entry

The agent made every cell a full-size click target, keeping the name as the row's single link for keyboard and screen-reader users. It then verified clicks at every corner of every cell.

> can we add the ability to view the resume within the leads UI without downloading? An in-app view. Additionally, can we add a button on that page that lets the attorney easily contact the client? I know you can click the email link, but that's not the most visible/intuitive

The agent added:
- **PDF:** embedded with the browser's own viewer.
- **Word (DOCX):** converted to sanitized HTML and shown in a locked-down frame, with limits against zip bombs.
- **Old Word (.doc):** download only.
- **Contact bar:** a prefilled "Email {name}" button.

It tested all of this with real PDF and Word uploads.

> The emails did not follow our style guides

The agent rebuilt the emails on one shared, email-safe layout that follows the style guide, and added an Email section to the guide.

> The attorney email has a non-working link to the Resume, just the resume filename in plaintext. That seems useless. Just omit the resume entry in the attorney email

The agent removed it from the HTML and plain-text versions and added a test so it can't return.

> did we address all the tech requirements?

The agent audited each requirement against the repo and the live CI results, and flagged what was built but under-documented.

> is all the documentation up to date? all of it?

The agent checked every doc and code comment against the code and fixed what had drifted: the architecture diagram, repo layout, test coverage and style guide components.

## 3. Attribution

Every commit written by the agent is authored as `Claude` and carries a `Co-Authored-By: Claude` trailer. [`NOTES.md`](../NOTES.md) maps agent-generated vs. human work across the repo.
