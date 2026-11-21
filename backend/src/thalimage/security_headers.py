"""Response headers that keep the app out of other sites' frames.

A page on another site can frame the app and place its own content over a
Delete, Merge or confirm button; the click then reaches the app as a
same-origin write, which the cross-site write guard allows by design. No
response may be framed, and the browser must not guess a different type for
what the app serves.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SecurityHeaders:
    """Set the framing and MIME-sniffing headers on every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Content-Security-Policy"] = "frame-ancestors 'none'"
                headers["X-Frame-Options"] = "DENY"
                headers["X-Content-Type-Options"] = "nosniff"
            await send(message)

        await self.app(scope, receive, send_with_headers)
