"""Telemetry helpers: event decorator for lightweight tracking."""
from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, Dict

from fastapi import Request

from src.telemetry import log_event


def track_event(event_name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator to emit a telemetry event after a successful handler call.

    Adds best-effort context: client host, path, method. Swallows telemetry errors.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            try:
                request: Request | None = kwargs.get("request")  # present if endpoint accepts Request
                ctx: Dict[str, Any] = {}
                if request is not None:
                    ctx.update({
                        "path": str(request.url.path),
                        "method": request.method,
                        "client": getattr(request.client, "host", None),
                    })
                await log_event(event_name, ctx)
            except Exception:
                # Never fail user requests due to telemetry
                pass
            return result

        return wrapper

    return decorator
