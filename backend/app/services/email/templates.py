from jinja2 import Environment, PackageLoader, select_autoescape

from app.core.config import Settings
from app.models import EmailKind, Lead
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
}

_TEMPLATES = {
    EmailKind.PROSPECT_CONFIRMATION: "prospect_confirmation",
    EmailKind.ATTORNEY_NOTIFICATION: "attorney_notification",
}


def render_email(kind: EmailKind, lead: Lead, recipient: str, settings: Settings) -> EmailMessage:
    context = {
        "lead": lead,
        "lead_url": f"{settings.web_origin.rstrip('/')}/leads/{lead.id}",
    }
    name = _TEMPLATES[kind]
    return EmailMessage(
        to=recipient,
        subject=_SUBJECTS[kind].format(name=lead.full_name),
        html=_env.get_template(f"{name}.html").render(context),
        text=_env.get_template(f"{name}.txt").render(context),
        # Let the attorney reply straight to the prospect from the notification.
        reply_to=lead.email if kind is EmailKind.ATTORNEY_NOTIFICATION else None,
    )
