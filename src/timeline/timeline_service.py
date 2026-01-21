"""
Activity Timeline Service
=========================
Unified timeline tracking all contact interactions and activities.
Aggregates events from email, meetings, calls, notes, and integrations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Types of timeline events."""
    # Email events
    EMAIL_SENT = "email_sent"
    EMAIL_DELIVERED = "email_delivered"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    EMAIL_UNSUBSCRIBED = "email_unsubscribed"
    
    # Meeting events
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_CONFIRMED = "meeting_confirmed"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_COMPLETED = "meeting_completed"
    MEETING_NO_SHOW = "meeting_no_show"
    
    # Call events
    CALL_SCHEDULED = "call_scheduled"
    CALL_COMPLETED = "call_completed"
    CALL_MISSED = "call_missed"
    VOICEMAIL_LEFT = "voicemail_left"
    
    # Contact events
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_MERGED = "contact_merged"
    CONTACT_SCORED = "contact_scored"
    CONTACT_ASSIGNED = "contact_assigned"
    
    # Deal events
    DEAL_CREATED = "deal_created"
    DEAL_UPDATED = "deal_updated"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    
    # Engagement events
    PAGE_VIEWED = "page_viewed"
    FORM_SUBMITTED = "form_submitted"
    DOCUMENT_VIEWED = "document_viewed"
    LINK_CLICKED = "link_clicked"
    
    # Task events
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    
    # Note events
    NOTE_ADDED = "note_added"
    COMMENT_ADDED = "comment_added"
    
    # Integration events
    HUBSPOT_SYNCED = "hubspot_synced"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    
    # Segment events
    SEGMENT_ENTERED = "segment_entered"
    SEGMENT_EXITED = "segment_exited"
    
    # Other
    CUSTOM = "custom"


class EventSource(str, Enum):
    """Sources of timeline events."""
    SYSTEM = "system"
    USER = "user"
    EMAIL = "email"
    CALENDAR = "calendar"
    HUBSPOT = "hubspot"
    WEBSITE = "website"
    WORKFLOW = "workflow"
    API = "api"
    IMPORT = "import"


@dataclass
class TimelineEvent:
    """A single event in the timeline."""
    id: str
    contact_id: str
    event_type: EventType
    source: EventSource
    title: str
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    actor_id: Optional[str] = None  # User who triggered the event
    actor_name: Optional[str] = None
    related_entity_type: Optional[str] = None  # email, meeting, deal, etc.
    related_entity_id: Optional[str] = None
    is_important: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "event_type": self.event_type.value,
            "source": self.source.value,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "is_important": self.is_important,
        }


class TimelineService:
    """
    Manages unified activity timelines for contacts.
    """
    
    def __init__(self):
        self.events: dict[str, list[TimelineEvent]] = {}  # contact_id -> events
        self.global_events: list[TimelineEvent] = []  # For system-wide events
    
    def record_event(
        self,
        contact_id: str,
        event_type: EventType,
        title: str,
        description: str = "",
        source: EventSource = EventSource.SYSTEM,
        metadata: dict = None,
        actor_id: str = None,
        actor_name: str = None,
        related_entity_type: str = None,
        related_entity_id: str = None,
        is_important: bool = False,
        timestamp: datetime = None,
    ) -> TimelineEvent:
        """Record a new event in the timeline."""
        event = TimelineEvent(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            event_type=event_type,
            source=source,
            title=title,
            description=description,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata or {},
            actor_id=actor_id,
            actor_name=actor_name,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_important=is_important,
        )
        
        if contact_id not in self.events:
            self.events[contact_id] = []
        
        self.events[contact_id].append(event)
        self.global_events.append(event)
        
        logger.info(
            "timeline_event_recorded",
            contact_id=contact_id,
            event_type=event_type.value,
            event_id=event.id,
        )
        
        return event
    
    def get_contact_timeline(
        self,
        contact_id: str,
        limit: int = 50,
        offset: int = 0,
        event_types: list[EventType] = None,
        sources: list[EventSource] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        important_only: bool = False,
    ) -> list[TimelineEvent]:
        """Get timeline for a specific contact."""
        events = self.events.get(contact_id, [])
        
        # Apply filters
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        if sources:
            events = [e for e in events if e.source in sources]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        if important_only:
            events = [e for e in events if e.is_important]
        
        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        return events[offset:offset + limit]
    
    def get_global_timeline(
        self,
        limit: int = 100,
        offset: int = 0,
        event_types: list[EventType] = None,
        sources: list[EventSource] = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> list[TimelineEvent]:
        """Get global timeline across all contacts."""
        events = self.global_events.copy()
        
        # Apply filters
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        
        if sources:
            events = [e for e in events if e.source in sources]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        # Sort by timestamp descending
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)
        
        return events[offset:offset + limit]
    
    def get_recent_activity(
        self,
        contact_id: str,
        hours: int = 24,
    ) -> list[TimelineEvent]:
        """Get recent activity for a contact."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return self.get_contact_timeline(
            contact_id=contact_id,
            start_date=cutoff,
        )
    
    def get_activity_summary(
        self,
        contact_id: str,
        days: int = 30,
    ) -> dict:
        """Get activity summary for a contact."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        events = self.get_contact_timeline(
            contact_id=contact_id,
            start_date=cutoff,
            limit=1000,
        )
        
        # Count by type
        type_counts = {}
        for event in events:
            event_type = event.event_type.value
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Count by source
        source_counts = {}
        for event in events:
            source = event.source.value
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Find engagement metrics
        emails_sent = type_counts.get("email_sent", 0)
        emails_opened = type_counts.get("email_opened", 0)
        emails_clicked = type_counts.get("email_clicked", 0)
        emails_replied = type_counts.get("email_replied", 0)
        meetings = type_counts.get("meeting_completed", 0)
        
        return {
            "contact_id": contact_id,
            "period_days": days,
            "total_events": len(events),
            "events_by_type": type_counts,
            "events_by_source": source_counts,
            "engagement": {
                "emails_sent": emails_sent,
                "emails_opened": emails_opened,
                "emails_clicked": emails_clicked,
                "emails_replied": emails_replied,
                "open_rate": (emails_opened / emails_sent * 100) if emails_sent > 0 else 0,
                "click_rate": (emails_clicked / emails_sent * 100) if emails_sent > 0 else 0,
                "reply_rate": (emails_replied / emails_sent * 100) if emails_sent > 0 else 0,
                "meetings": meetings,
            },
            "last_activity": events[0].timestamp.isoformat() if events else None,
        }
    
    def get_activity_trends(
        self,
        contact_id: str = None,
        days: int = 7,
    ) -> dict:
        """Get activity trends over time."""
        events = (
            self.events.get(contact_id, []) if contact_id
            else self.global_events
        )
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        events = [e for e in events if e.timestamp >= cutoff]
        
        # Group by day
        daily_counts = {}
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_counts[date] = 0
        
        for event in events:
            date = event.timestamp.strftime("%Y-%m-%d")
            if date in daily_counts:
                daily_counts[date] += 1
        
        # Sort by date
        sorted_dates = sorted(daily_counts.items())
        
        return {
            "contact_id": contact_id,
            "period_days": days,
            "daily_activity": [
                {"date": date, "count": count}
                for date, count in sorted_dates
            ],
            "total_events": sum(daily_counts.values()),
            "average_per_day": sum(daily_counts.values()) / days if days > 0 else 0,
        }
    
    def record_email_event(
        self,
        contact_id: str,
        event_type: EventType,
        email_id: str,
        subject: str,
        metadata: dict = None,
    ) -> TimelineEvent:
        """Record an email-related event."""
        titles = {
            EventType.EMAIL_SENT: f"Email sent: {subject}",
            EventType.EMAIL_DELIVERED: f"Email delivered: {subject}",
            EventType.EMAIL_OPENED: f"Email opened: {subject}",
            EventType.EMAIL_CLICKED: f"Link clicked in: {subject}",
            EventType.EMAIL_REPLIED: f"Reply received: {subject}",
            EventType.EMAIL_BOUNCED: f"Email bounced: {subject}",
            EventType.EMAIL_UNSUBSCRIBED: f"Unsubscribed from: {subject}",
        }
        
        return self.record_event(
            contact_id=contact_id,
            event_type=event_type,
            title=titles.get(event_type, f"Email event: {subject}"),
            source=EventSource.EMAIL,
            metadata=metadata or {},
            related_entity_type="email",
            related_entity_id=email_id,
            is_important=event_type in [EventType.EMAIL_REPLIED, EventType.EMAIL_BOUNCED],
        )
    
    def record_meeting_event(
        self,
        contact_id: str,
        event_type: EventType,
        meeting_id: str,
        meeting_title: str,
        metadata: dict = None,
    ) -> TimelineEvent:
        """Record a meeting-related event."""
        titles = {
            EventType.MEETING_SCHEDULED: f"Meeting scheduled: {meeting_title}",
            EventType.MEETING_CONFIRMED: f"Meeting confirmed: {meeting_title}",
            EventType.MEETING_CANCELLED: f"Meeting cancelled: {meeting_title}",
            EventType.MEETING_COMPLETED: f"Meeting completed: {meeting_title}",
            EventType.MEETING_NO_SHOW: f"No show: {meeting_title}",
        }
        
        return self.record_event(
            contact_id=contact_id,
            event_type=event_type,
            title=titles.get(event_type, f"Meeting event: {meeting_title}"),
            source=EventSource.CALENDAR,
            metadata=metadata or {},
            related_entity_type="meeting",
            related_entity_id=meeting_id,
            is_important=event_type in [EventType.MEETING_COMPLETED, EventType.MEETING_SCHEDULED],
        )
    
    def delete_event(self, event_id: str) -> bool:
        """Delete an event from the timeline."""
        for contact_id, events in self.events.items():
            for i, event in enumerate(events):
                if event.id == event_id:
                    events.pop(i)
                    # Also remove from global
                    self.global_events = [e for e in self.global_events if e.id != event_id]
                    return True
        return False
    
    def get_event(self, event_id: str) -> Optional[TimelineEvent]:
        """Get a specific event by ID."""
        for event in self.global_events:
            if event.id == event_id:
                return event
        return None
    
    def get_contact_count(self, contact_id: str) -> int:
        """Get the total number of events for a contact."""
        return len(self.events.get(contact_id, []))


# Singleton instance
_service: Optional[TimelineService] = None


def get_timeline_service() -> TimelineService:
    """Get the timeline service singleton."""
    global _service
    if _service is None:
        _service = TimelineService()
    return _service
