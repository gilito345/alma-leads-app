"""ASGI middleware that caps request body size while the body is still streaming in.

Starlette parses a whole multipart body before the endpoint runs, so checking the file size
inside the route is too late to stop someone uploading gigabytes. This counts bytes as they
arrive and aborts as soon as the limit is crossed.
"""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import RequestTooLargeError, error_body


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_body_bytes:
            await self._reject(send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise RequestTooLargeError(self.max_body_bytes)
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except RequestTooLargeError:
            # Normally the app's exception handler renders this; this is the fallback for
            # when the error escapes (e.g. raised outside a route).
            if not response_started:
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps(
            error_body("payload_too_large", f"Request body exceeds {self.max_body_bytes} bytes")
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
