import logging
import time
from uuid import UUID, uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("mealforge.requests")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get("x-request-id", "")
        try:
            request_id = str(UUID(incoming)) if len(incoming) <= 36 else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.monotonic()
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["Cache-Control"] = "no-store"
                logger.info(
                    "request_id=%s method=%s status=%s duration_ms=%.2f",
                    request_id,
                    scope["method"],
                    message["status"],
                    (time.monotonic() - started) * 1000,
                )
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # Keep exception/payload/DSN details out of the ASGI server's error logs.
            logger.error("request_id=%s error_code=INTERNAL_ERROR", request_id)
            if response_started:
                raise RuntimeError("Nie udało się zakończyć odpowiedzi.") from None
            response = JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Wystąpił wewnętrzny błąd usługi.",
                    "request_id": request_id,
                },
                media_type="application/problem+json",
            )
            await response(scope, receive, send_with_id)
