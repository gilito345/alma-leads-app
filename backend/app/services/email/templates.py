from urllib.parse import urlencode

from jinja2 import Environment, PackageLoader, select_autoescape

from app.core.config import Settings
from app.models import EmailKind, Lead, User
from app.services.email.base import EmailMessage

_env = Environment(
    loader=PackageLoader("app", "templates/email"),
    autoescape=select_autoescape(enabled_extensions=("html",), default_for_string=False),
    trim_blocks=True,
    lstrip_blocks=True,
)

_SUBJECTS = {
    EmailKind.PROSPECT_CONFIRMATION: "We received your information",
    EmailKind.ATTORNEY_NOTIFICATION: "New lead: {name}",
    EmailKind.ATTORNEY_INVITE: "You're invited to the leads dashboard",
    EmailKind.PASSWORD_RESET: "Reset your password",
}

_TEMPLATES = {
    EmailKind.PROSPECT_CONFIRMATION: "prospect_confirmation",
    EmailKind.ATTORNEY_NOTIFICATION: "attorney_notification",
    EmailKind.ATTORNEY_INVITE: "attorney_invite",
    EmailKind.PASSWORD_RESET: "password_reset",
}

# The web app page that redeems each account link.
_LINK_PAGES = {
    EmailKind.ATTORNEY_INVITE: "/accept-invite",
    EmailKind.PASSWORD_RESET: "/reset-password",
}


def render_email(kind: EmailKind, lead: Lead, recipient: str, settings: Settings) -> EmailMessage:
    """An email about a lead: the prospect's confirmation or the attorney's notification."""
    context = {
        "lead": lead,
        "lead_url": f"{settings.web_origin.rstrip('/')}/leads/{lead.id}",
    }
    return _render(
        kind,
        context,
        recipient,
        subject=_SUBJECTS[kind].format(name=lead.full_name),
        # Let the attorney reply straight to the prospect from the notification.
        reply_to=lead.email if kind is EmailKind.ATTORNEY_NOTIFICATION else None,
    )


def render_account_email(
    kind: EmailKind, user: User, token_hash: str, settings: Settings
) -> EmailMessage:
    """An invite or password-reset email carrying a single-use link to the web app."""
    query = urlencode({"token": token_hash})
    context = {
        "user": user,
        "link": f"{settings.web_origin.rstrip('/')}{_LINK_PAGES[kind]}?{query}",
        "expiry_hours": settings.auth_link_expiry_hours,
    }
    return _render(kind, context, user.email, subject=_SUBJECTS[kind])


def _render(
    kind: EmailKind,
    context: dict[str, object],
    recipient: str,
    *,
    subject: str,
    reply_to: str | None = None,
) -> EmailMessage:
    name = _TEMPLATES[kind]
    return EmailMessage(
        to=recipient,
        subject=subject,
        html=_env.get_template(f"{name}.html").render(context),
        text=_env.get_template(f"{name}.txt").render(context),
        reply_to=reply_to,
    )
