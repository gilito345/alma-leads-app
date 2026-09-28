# Coding-Agent Usage

## 1. Writeup

**Tools.** [Claude Code](https://claude.com/claude-code) (desktop app, Claude Opus 5.5) over two sessions, with its built-in browser for walking through the running app and sampling [tryalma.com](https://www.tryalma.com) for the style guide. Docker ran everything, tests included.

**Delegated vs. kept.** The agent wrote all code, tests and docs (see [`NOTES.md`](../NOTES.md)). I kept what needs judgment or accountability: scope and product decisions (invite-only accounts, the in-page resume viewer, the contact button), security trade-offs (24-hour invite links, `.doc` as download-only), secrets (the Resend key went into `.env` by hand, never through the agent), and review. I tested every change in the running app and sent back anything that read or behaved wrong, such as a "Free consultation" label promising something we don't offer. The rules were mine too: full CI plus a browser walkthrough before each commit, one commit per change. The agent is fast and consistent across FastAPI, SQL, Next.js and tests; scope, risk and "does this feel right to an attorney" are calls I'm accountable for.

**Where it got it wrong.** To block public sign-up, the agent set `enable_signup = false` under `[auth.email]` in `supabase/config.toml`. In the Supabase CLI that disables the whole email provider, so password sign-in broke too, even though the agent reported the stack as healthy. I caught it by using the app as an attorney would: creating the first account ended in "Authentication service unavailable". The API logs showed the account was created but its sign-in was refused (`email_provider_disabled`). The fix blocks sign-up with the right switch (`[auth] enable_signup = false`) and leaves the email provider on. We verified both behaviours against Supabase directly and added a comment so nobody "tightens" it back. A follow-up audit found a second latent issue: the tests used `.test` addresses that email validation always rejects, so the suite had never passed. Running CI from pinned lock files exposed it, and it's fixed.

## 2. Prompt log (selected excerpts)

Excerpts from the second Claude Code session. Prompts are quoted exactly as typed; the line under each summarises what the agent did.

> build 1 and 2, and disable email/password signup for the internal UI, rely only on auth

*Following a comparison of Supabase Auth features (1 = email invites, 2 = password reset).* The agent checked Supabase's invite, verify and recovery endpoints against the local stack before writing code. It then built invite-only accounts: invite and reset emails go through the existing outbox, the worker creates the one-time link at send time, and resets sign out other sessions. It added 20+ tests and walked through both flows in the browser.

> how would we add MFA for attorneys? Don't implement it yet just discuss it with me

The agent proposed authenticator-app MFA enforced by the API (assurance level `aal2`), weighed recovery options, and flagged that password reset must not bypass the second factor. Recorded as a next step in the design doc.

> https://www.tryalma.com/ make sure you navigate around to various pages for a better sampling

The agent sampled six pages at desktop and phone widths and read the site's own CSS variables. It wrote `docs/STYLE_GUIDE.md` (with Figtree standing in for the licensed Gellix font) and restyled the app.

> Is there better wording than "Free Consultation" where does that even come from

The agent traced the label to the first session's web-app commit, noted it was a pricing promise nothing else backed, and proposed alternatives; I chose "Talk to an attorney".

> When i hover over the entries in the leads list it gets highlighted, which is good, but it only actually opens the lead when the you click on the name itself, which is unintuitive, it should open regardless where exactly you click on the entry

The agent made every cell a full-size click target while keeping the name as the row's single link for keyboard and screen-reader users, then verified click targets in every cell, corners included.

> can we add the ability to view the resume within the leads UI without downloading? An in-app view. Additionally, can we add a button on that page that lets the attorney easily contact the client? I know you can click the email link, but that's not the most visible/intuitive

The agent added PDFs embedded with the browser's viewer, DOCX converted to sanitized HTML in a sandboxed frame (with zip-bomb limits), and `.doc` as download-only. It added a contact bar with a prefilled "Email {name}" button, then tested with real PDF and DOCX uploads.

> The emails did not follow our style guides

The agent rebuilt the emails on one shared, email-safe layout that follows the style guide, and added an Email section to the guide.

> The attorney email has a non-working link to the Resume, just the resume filename in plaintext. That seems useless. Just omit the resume entry in the attorney email

The agent removed it from both the HTML and plain-text versions and added a test assertion so it can't return.

> did we address all the tech requirements?

The agent audited each requirement against the repo and live CI results, and flagged what was built but under-documented.

> is all the documentation up to date? all of it?

The agent checked every doc and code comment against the code and fixed what had drifted (architecture diagram, repo layout, test coverage, style guide components).

## 3. Attribution

Every commit written by the agent carries a `Co-Authored-By: Claude` trailer and is authored as `Claude`. [`NOTES.md`](../NOTES.md) maps agent-generated vs. human work across the repo.
