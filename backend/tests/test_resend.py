import json

import httpx
import pytest
import respx

from app.services.email import EmailMessage, EmailSendError, ResendEmailSender
from app.services.email.resend import RESEND_API_URL

MESSAGE = EmailMessage(
    to="ada@example.com", subject="Hi", html="<p>Hi</p>", text="Hi", reply_to="x@example.com"
)


@pytest.fixture
def sender() -> ResendEmailSender:
    return ResendEmailSender("re_test_key", "Leads <leads@firm.test>")


@respx.mock
def test_sends_expected_request(sender: ResendEmailSender) -> None:
    route = respx.post(RESEND_API_URL).mock(return_value=httpx.Response(200, json={"id": "em_1"}))

    assert sender.send(MESSAGE, idempotency_key="key-1") == "em_1"

    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer re_test_key"
    assert request.headers["Idempotency-Key"] == "key-1"
    assert json.loads(request.content) == {
        "from": "Leads <leads@firm.test>",
        "to": ["ada@example.com"],
        "subject": "Hi",
        "html": "<p>Hi</p>",
        "text": "Hi",
        "reply_to": "x@example.com",
    }


@pytest.mark.parametrize(("status", "retryable"), [(500, True), (503, True), (429, True)])
@respx.mock
def test_transient_errors_are_retryable(
    sender: ResendEmailSender, status: int, retryable: bool
) -> None:
    respx.post(RESEND_API_URL).mock(return_value=httpx.Response(status, text="nope"))
    with pytest.raises(EmailSendError) as exc_info:
        sender.send(MESSAGE, idempotency_key="k")
    assert exc_info.value.retryable is retryable


@pytest.mark.parametrize("status", [400, 401, 403, 422])
@respx.mock
def test_client_errors_are_permanent(sender: ResendEmailSender, status: int) -> None:
    respx.post(RESEND_API_URL).mock(return_value=httpx.Response(status, json={"message": "bad"}))
    with pytest.raises(EmailSendError) as exc_info:
        sender.send(MESSAGE, idempotency_key="k")
    assert exc_info.value.retryable is False


@respx.mock
def test_network_errors_are_retryable(sender: ResendEmailSender) -> None:
    respx.post(RESEND_API_URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(EmailSendError) as exc_info:
        sender.send(MESSAGE, idempotency_key="k")
    assert exc_info.value.retryable is True
