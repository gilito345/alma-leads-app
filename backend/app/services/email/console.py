import logging

from app.services.email.base import EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Logs emails instead of sending them. Used when no Resend API key is configured."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage, *, idempotency_key: str) -> str | None:
        self.sent.append(message)
        logger.info(
            "Email (console, not delivered) to=%s subject=%r key=%s\n%s",
            message.to,
            message.subject,
            idempotency_key,
            message.text,
        )
        return None
