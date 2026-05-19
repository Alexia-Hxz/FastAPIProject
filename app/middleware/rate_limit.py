import time
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from fastapi import HTTPException
from app.config import settings


class RateLimitMiddleware:
    """Pure ASGI rate limiter — does not buffer streaming responses."""

    def __init__(self, app: ASGIApp, max_requests: int = 60, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not settings.RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/api/v1/ai"):
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries for this IP
        if client_ip in self._store:
            self._store[client_ip] = [t for t in self._store[client_ip] if t > window_start]
            if not self._store[client_ip]:
                del self._store[client_ip]

        if len(self._store.get(client_ip, [])) >= self.max_requests:
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"detail":"Too many requests"}',
            })
            return

        self._store.setdefault(client_ip, []).append(now)
        await self.app(scope, receive, send)
