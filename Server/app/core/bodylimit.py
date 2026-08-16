from fastapi import HTTPException, status
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


# An HTTPException, not a bare one: FastAPI wraps body reads in
# `except HTTPException: raise / except Exception: -> 400`, so anything else
# raised out of receive() is rewritten to "error parsing the body" before it can
# reach the handler below.
class _TooLarge(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Request body too large",
        )


class BodySizeLimit:
    # Two limits chosen by content-type, not by path: JSON bodies are tiny and
    # only the cover upload has any business being large. That route streams
    # against its own cap in process_cover (SECURITY.md 4.2) — this is the outer
    # bound that stops an oversized body ever reaching it.
    def __init__(self, app: ASGIApp, *, json_limit: int, upload_limit: int) -> None:
        self.app = app
        self.json_limit = json_limit
        self.upload_limit = upload_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = Headers(scope=scope)
        limit = (
            self.upload_limit
            if headers.get("content-type", "").startswith("multipart/form-data")
            else self.json_limit
        )

        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return await self._refuse(send)

        seen = 0
        started = False

        # The declared length above covers every well-behaved client. This
        # catches the one that sends chunked with no content-length at all.
        async def counting_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    raise _TooLarge()
            return message

        async def watching_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, watching_send)
        except _TooLarge:
            # Once the app has begun responding the status line is already on the
            # wire and a 413 can no longer replace it.
            if not started:
                await self._refuse(send)

    @staticmethod
    async def _refuse(send: Send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
