"""
Events Module - Activity and Event Tracking
============================================
Handles events, activities, and timeline management.
"""

from .event_service import (
    EventService,
    Event,
    EventType,
    EventCategory,
    ActivityFeed,
    get_event_service,
)

__all__ = [
    "EventService",
    "Event",
    "EventType",
    "EventCategory",
    "ActivityFeed",
    "get_event_service",
]
