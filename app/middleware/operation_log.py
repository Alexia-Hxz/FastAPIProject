import time
import json
import uuid
import logging
from urllib.parse import parse_qs
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from app.core.database import async_session
from app.models.operation_log import OperationLog

logger = logging.getLogger(__name__)


SKIP_LOG_PATHS = {"/api/v1/logs", "/app", "/docs", "/redoc", "/api/v1/ai/log-analysis"}


class OperationLogMiddleware:
    """Pure ASGI middleware — does not buffer streaming responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip logging for log-management URLs to avoid feedback loop
        path = scope.get("path", "")
        for skip in SKIP_LOG_PATHS:
            if path.startswith(skip):
                await self.app(scope, receive, send)
                return

        start_time = time.time()
        response_status = [200]  # mutable container

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.time() - start_time) * 1000)

            # Collect request info from scope
            request_method = scope.get("method", "")
            request_url = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
            query_params = dict(
                (k, v[0] if len(v) == 1 else v)
                for k, v in parse_qs(query_string).items()
            ) if query_string else {}

            # Get user from scope state (set by get_current_user dependency)
            scope_state = scope.get("state", {})
            user_id = scope_state.get("current_user_id") if isinstance(scope_state, dict) else getattr(scope_state, "current_user_id", None)
            username = scope_state.get("current_username") if isinstance(scope_state, dict) else getattr(scope_state, "current_username", None)

            # Get client IP
            client = scope.get("client")
            ip_address = client[0] if client else None

            # Get user agent
            user_agent = None
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"user-agent":
                    user_agent = header_value.decode("utf-8", errors="replace")
                    break

            # Try to log (non-blocking, silent failure)
            try:
                log_entry = OperationLog(
                    user_id=uuid.UUID(str(user_id)) if user_id else None,
                    username=str(username) if username else None,
                    request_method=request_method,
                    request_url=request_url,
                    request_params=query_params,
                    request_body=None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    response_status=response_status[0],
                    duration_ms=duration_ms,
                )
                async with async_session() as db:
                    try:
                        db.add(log_entry)
                        await db.commit()
                    except Exception:
                        logger.debug("Failed to persist operation log", exc_info=True)
            except Exception:
                logger.debug("Failed to create operation log entry", exc_info=True)
