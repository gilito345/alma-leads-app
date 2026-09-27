from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str
    reply_to: str | None = None


class EmailSendError(Exception):
    """Sending failed. `retryable` says whether trying again later could succeed."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class EmailSender(Protocol):
    def send(self, message: EmailMessage, *, idempotency_key: str) -> str | None:
        """Send `message`; return the provider's message id if it gives one.

        `idempotency_key` must be stable across retries of the same logical email so the
        provider can drop duplicates.
        """
        ...
