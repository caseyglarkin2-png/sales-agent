"""
Activity Timeline Module
========================
Unified timeline of all contact activities and interactions.
"""

from src.timeline.timeline_service import (
    TimelineService,
    TimelineEvent,
    EventType,
    EventSource,
    get_timeline_service,
)

__all__ = [
    "TimelineService",
    "TimelineEvent",
    "EventType",
    "EventSource",
    "get_timeline_service",
]
