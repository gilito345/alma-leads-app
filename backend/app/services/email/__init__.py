from app.core.config import Settings
from app.services.email.base import EmailMessage, EmailSender, EmailSendError
from app.services.email.console import ConsoleEmailSender
from app.services.email.resend import ResendEmailSender
from app.services.email.templates import render_email


def build_email_sender(settings: Settings) -> EmailSender:
    if settings.resend_api_key:
        return ResendEmailSender(settings.resend_api_key.get_secret_value(), settings.email_from)
    return ConsoleEmailSender()


__all__ = [
    "ConsoleEmailSender",
    "EmailMessage",
    "EmailSendError",
    "EmailSender",
    "ResendEmailSender",
    "build_email_sender",
    "render_email",
]
