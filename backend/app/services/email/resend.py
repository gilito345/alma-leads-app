import logging

import httpx

from app.services.email.base import EmailMessage, EmailSendError

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailSender:
    """Sends email through Resend's HTTP API (https://resend.com/docs/api-reference)."""

    def __init__(
        self,
        api_key: str,
        from_address: str,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._from = from_address
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def send(self, message: EmailMessage, *, idempotency_key: str) -> str | None:
        payload: dict[str, object] = {
            "from": self._from,
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        try:
            response = self._client.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": idempotency_key,
                },
            )
        except httpx.HTTPError as exc:
            raise EmailSendError(f"Network error calling Resend: {exc}", retryable=True) from exc

        if response.is_success:
            message_id = response.json().get("id")
            return str(message_id) if message_id else None

        # 429 and 5xx are transient; other 4xx (bad key, unverified domain, invalid address)
        # won't fix themselves, so retrying would only delay the alert.
        retryable = response.status_code == 429 or response.status_code >= 500
        raise EmailSendError(
            f"Resend returned {response.status_code}: {response.text[:500]}",
            retryable=retryable,
        )
