"""FastAPI middleware for request tracing and context."""
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.logger import set_trace_id, get_trace_id


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace_id to requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add trace_id from header or generate new one."""
        # Try to get trace_id from request header
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        set_trace_id(trace_id)

        # Add trace_id to request state
        request.state.trace_id = trace_id

        # Process request
        response = await call_next(request)

        # Add trace_id to response headers
        response.headers["X-Trace-ID"] = trace_id

        return response
