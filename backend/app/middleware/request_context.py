"""
Request-context middleware.

Assigns a ``request_id`` to every request, makes it available to the rest of the
app via contextvars (so structured logs include it), and echoes it back in the
``X-Request-ID`` response header so support / the frontend can correlate errors.
"""

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, set_trace_context, reset_trace_context

logger = get_logger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        set_trace_context(request_id=request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request %s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )
            reset_trace_context()