"""Telemetry scaffolding for CaseyOS."""
from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, Dict
from datetime import datetime
import json

from src.logger import get_logger

_logger = get_logger("telemetry")


async def log_event(event: str, properties: Dict[str, Any] | None = None) -> None:
    payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "properties": properties or {},
    }
    _logger.info(json.dumps(payload))


def track_event(event_name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator to emit a telemetry event after a successful handler call."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            try:
                await log_event(event_name, {"function": func.__name__})
            except Exception:
                pass
            return result
        return wrapper
    return decorator

