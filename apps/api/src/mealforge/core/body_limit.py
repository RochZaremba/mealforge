import asyncio

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodyLimitMiddleware:
    """Bound actual bytes, including chunked requests, before JSON parsing."""

    def __init__(self, app: ASGIApp, limit: int = 16384) -> None:
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > self.limit:
                        response = JSONResponse(
                            status_code=413,
                            media_type="application/problem+json",
                            content={
                                "error_code": "BODY_TOO_LARGE",
                                "message": "Żądanie zawiera za dużo danych.",
                                "request_id": scope["state"]["request_id"],
                            },
                        )
                        await response(scope, receive, send)
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            response = JSONResponse(
                status_code=408,
                media_type="application/problem+json",
                content={
                    "error_code": "BODY_TIMEOUT",
                    "message": "Przekroczenie czasu przesyłania żądania.",
                    "request_id": scope["state"]["request_id"],
                },
            )
            await response(scope, receive, send)
            return
        delivered = False

        async def replay_receive() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)
