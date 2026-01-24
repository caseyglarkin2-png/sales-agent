"""Telemetry scaffolding for CaseyOS.

Event Types:
- recommendation_generated: APS score calculated for a recommendation
- recommendation_viewed: User viewed the Today's Moves list
- recommendation_accepted: User clicked Execute on a recommendation
- recommendation_dismissed: User clicked Skip on a recommendation
- action_executed: An action was performed (email sent, task created, etc.)
- action_failed: An action failed to execute
- outcome_recorded: An outcome was captured (reply, meeting, deal advance)
- signal_ingested: A new signal was captured from an external source
"""
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional
from datetime import datetime
import json

from src.logger import get_logger

_logger = get_logger("telemetry")


# =============================================================================
# Core Event Logging
# =============================================================================

async def log_event(
    event: str, 
    properties: Dict[str, Any] | None = None,
    item_id: Optional[str] = None,
    user: Optional[str] = None,
    aps_score: Optional[float] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """
    Log a telemetry event with structured properties.
    
    Args:
        event: Event name (e.g., "recommendation_accepted")
        properties: Additional event properties
        item_id: ID of the related item (recommendation, signal, etc.)
        user: User identifier
        aps_score: Action Priority Score if relevant
        duration_ms: Duration in milliseconds if relevant
    """
    payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "properties": properties or {},
    }
    
    # Add optional fields if provided
    if item_id:
        payload["item_id"] = item_id
    if user:
        payload["user"] = user
    if aps_score is not None:
        payload["aps_score"] = aps_score
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    
    _logger.info(json.dumps(payload))


# =============================================================================
# Specific Event Helpers
# =============================================================================

async def log_recommendation_generated(
    item_id: str,
    aps_score: float,
    action_type: str,
    drivers: Optional[Dict[str, float]] = None,
) -> None:
    """Log when a new recommendation is generated."""
    await log_event(
        "recommendation_generated",
        properties={
            "action_type": action_type,
            "drivers": drivers or {},
        },
        item_id=item_id,
        aps_score=aps_score,
    )


async def log_recommendation_accepted(
    item_id: str,
    user: str,
    aps_score: Optional[float] = None,
) -> None:
    """Log when a user accepts/executes a recommendation."""
    await log_event(
        "recommendation_accepted",
        item_id=item_id,
        user=user,
        aps_score=aps_score,
    )


async def log_recommendation_dismissed(
    item_id: str,
    user: str,
    reason: Optional[str] = None,
) -> None:
    """Log when a user dismisses/skips a recommendation."""
    await log_event(
        "recommendation_dismissed",
        properties={"reason": reason} if reason else None,
        item_id=item_id,
        user=user,
    )


async def log_action_executed(
    item_id: str,
    action_type: str,
    success: bool,
    duration_ms: float,
    error: Optional[str] = None,
) -> None:
    """Log when an action is executed (success or failure)."""
    event = "action_executed" if success else "action_failed"
    await log_event(
        event,
        properties={
            "action_type": action_type,
            "success": success,
            "error": error,
        },
        item_id=item_id,
        duration_ms=duration_ms,
    )


async def log_signal_ingested(
    signal_id: str,
    source: str,
    signal_type: str,
) -> None:
    """Log when a new signal is ingested."""
    await log_event(
        "signal_ingested",
        properties={
            "source": source,
            "signal_type": signal_type,
        },
        item_id=signal_id,
    )


async def log_outcome_recorded(
    item_id: str,
    outcome_type: str,
    outcome_value: Any,
) -> None:
    """Log when an outcome is recorded."""
    await log_event(
        "outcome_recorded",
        properties={
            "outcome_type": outcome_type,
            "outcome_value": outcome_value,
        },
        item_id=item_id,
    )


# =============================================================================
# Decorator for Automatic Tracking
# =============================================================================

def track_event(event_name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """
    Decorator to emit a telemetry event after a successful handler call.
    Also tracks execution duration.
    
    Usage:
        @track_event("recommendation_viewed")
        async def get_todays_moves():
            ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            try:
                await log_event(
                    event_name, 
                    properties={"function": func.__name__},
                    duration_ms=duration_ms,
                )
            except Exception:
                pass  # Never fail the request due to telemetry
            return result
        return wrapper
    return decorator

