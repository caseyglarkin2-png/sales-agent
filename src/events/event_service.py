"""
Event Service - Activity and Event Tracking
============================================
Handles events, activities, and timeline management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class EventType(str, Enum):
    """Event type."""
    # Communication
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    
    # Calls
    CALL_MADE = "call_made"
    CALL_RECEIVED = "call_received"
    CALL_MISSED = "call_missed"
    VOICEMAIL_LEFT = "voicemail_left"
    
    # Meetings
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_NO_SHOW = "meeting_no_show"
    
    # Tasks
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    
    # Notes
    NOTE_ADDED = "note_added"
    
    # Documents
    DOCUMENT_SENT = "document_sent"
    DOCUMENT_VIEWED = "document_viewed"
    DOCUMENT_SIGNED = "document_signed"
    
    # Deals
    DEAL_CREATED = "deal_created"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    DEAL_VALUE_CHANGED = "deal_value_changed"
    
    # Contacts
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_MERGED = "contact_merged"
    
    # Quotes/Proposals
    QUOTE_SENT = "quote_sent"
    QUOTE_VIEWED = "quote_viewed"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    
    # Invoices
    INVOICE_SENT = "invoice_sent"
    INVOICE_PAID = "invoice_paid"
    INVOICE_OVERDUE = "invoice_overdue"
    
    # Web
    PAGE_VIEWED = "page_viewed"
    FORM_SUBMITTED = "form_submitted"
    LINK_CLICKED = "link_clicked"
    
    # Custom
    CUSTOM = "custom"


class EventCategory(str, Enum):
    """Event category for grouping."""
    COMMUNICATION = "communication"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"
    DOCUMENT = "document"
    DEAL = "deal"
    CONTACT = "contact"
    QUOTE = "quote"
    INVOICE = "invoice"
    WEB = "web"
    SYSTEM = "system"
    CUSTOM = "custom"


# Map event types to categories
EVENT_CATEGORIES = {
    EventType.EMAIL_SENT: EventCategory.COMMUNICATION,
    EventType.EMAIL_OPENED: EventCategory.COMMUNICATION,
    EventType.EMAIL_CLICKED: EventCategory.COMMUNICATION,
    EventType.EMAIL_REPLIED: EventCategory.COMMUNICATION,
    EventType.EMAIL_BOUNCED: EventCategory.COMMUNICATION,
    EventType.CALL_MADE: EventCategory.COMMUNICATION,
    EventType.CALL_RECEIVED: EventCategory.COMMUNICATION,
    EventType.CALL_MISSED: EventCategory.COMMUNICATION,
    EventType.VOICEMAIL_LEFT: EventCategory.COMMUNICATION,
    EventType.MEETING_SCHEDULED: EventCategory.MEETING,
    EventType.MEETING_COMPLETED: EventCategory.MEETING,
    EventType.MEETING_CANCELLED: EventCategory.MEETING,
    EventType.MEETING_NO_SHOW: EventCategory.MEETING,
    EventType.TASK_CREATED: EventCategory.TASK,
    EventType.TASK_COMPLETED: EventCategory.TASK,
    EventType.TASK_OVERDUE: EventCategory.TASK,
    EventType.NOTE_ADDED: EventCategory.NOTE,
    EventType.DOCUMENT_SENT: EventCategory.DOCUMENT,
    EventType.DOCUMENT_VIEWED: EventCategory.DOCUMENT,
    EventType.DOCUMENT_SIGNED: EventCategory.DOCUMENT,
    EventType.DEAL_CREATED: EventCategory.DEAL,
    EventType.DEAL_STAGE_CHANGED: EventCategory.DEAL,
    EventType.DEAL_WON: EventCategory.DEAL,
    EventType.DEAL_LOST: EventCategory.DEAL,
    EventType.DEAL_VALUE_CHANGED: EventCategory.DEAL,
    EventType.CONTACT_CREATED: EventCategory.CONTACT,
    EventType.CONTACT_UPDATED: EventCategory.CONTACT,
    EventType.CONTACT_MERGED: EventCategory.CONTACT,
    EventType.QUOTE_SENT: EventCategory.QUOTE,
    EventType.QUOTE_VIEWED: EventCategory.QUOTE,
    EventType.QUOTE_ACCEPTED: EventCategory.QUOTE,
    EventType.QUOTE_REJECTED: EventCategory.QUOTE,
    EventType.INVOICE_SENT: EventCategory.INVOICE,
    EventType.INVOICE_PAID: EventCategory.INVOICE,
    EventType.INVOICE_OVERDUE: EventCategory.INVOICE,
    EventType.PAGE_VIEWED: EventCategory.WEB,
    EventType.FORM_SUBMITTED: EventCategory.WEB,
    EventType.LINK_CLICKED: EventCategory.WEB,
    EventType.CUSTOM: EventCategory.CUSTOM,
}


@dataclass
class Event:
    """An event or activity."""
    id: str
    event_type: EventType
    category: EventCategory
    
    # Description
    title: str
    description: Optional[str] = None
    
    # Related entities
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Related object
    object_type: Optional[str] = None  # email, call, meeting, etc.
    object_id: Optional[str] = None
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Source
    source: str = "app"  # app, api, import, system
    
    # Timing
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: Optional[int] = None
    
    # Visibility
    is_private: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


@dataclass
class ActivityFeed:
    """Activity feed configuration."""
    id: str
    name: str
    
    # Filters
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    deal_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Event type filters
    event_types: list[EventType] = field(default_factory=list)
    categories: list[EventCategory] = field(default_factory=list)
    
    # Date range
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EventAggregation:
    """Aggregated event data."""
    period: str  # day, week, month
    start_date: datetime
    end_date: datetime
    
    total_events: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    by_user: dict[str, int] = field(default_factory=dict)


class EventService:
    """Service for event and activity management."""
    
    def __init__(self):
        self.events: dict[str, Event] = {}
        self.feeds: dict[str, ActivityFeed] = {}
    
    # Event operations
    async def log_event(
        self,
        event_type: EventType,
        title: str,
        description: Optional[str] = None,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        object_type: Optional[str] = None,
        object_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        source: str = "app",
        occurred_at: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Event:
        """Log an event."""
        category = EVENT_CATEGORIES.get(event_type, EventCategory.CUSTOM)
        
        event = Event(
            id=str(uuid.uuid4()),
            event_type=event_type,
            category=category,
            title=title,
            description=description,
            contact_id=contact_id,
            account_id=account_id,
            deal_id=deal_id,
            user_id=user_id,
            object_type=object_type,
            object_id=object_id,
            metadata=metadata or {},
            source=source,
            occurred_at=occurred_at or datetime.utcnow(),
            duration_seconds=duration_seconds,
            created_by=created_by,
        )
        
        self.events[event.id] = event
        return event
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get an event by ID."""
        return self.events.get(event_id)
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    async def list_events(
        self,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_types: Optional[list[EventType]] = None,
        categories: Optional[list[EventCategory]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[list[Event], int]:
        """List events with filters."""
        events = list(self.events.values())
        
        if contact_id:
            events = [e for e in events if e.contact_id == contact_id]
        if account_id:
            events = [e for e in events if e.account_id == account_id]
        if deal_id:
            events = [e for e in events if e.deal_id == deal_id]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        if categories:
            events = [e for e in events if e.category in categories]
        if from_date:
            events = [e for e in events if e.occurred_at >= from_date]
        if to_date:
            events = [e for e in events if e.occurred_at <= to_date]
        if source:
            events = [e for e in events if e.source == source]
        
        events.sort(key=lambda e: e.occurred_at, reverse=True)
        total = len(events)
        
        return events[offset:offset + limit], total
    
    # Timeline methods
    async def get_contact_timeline(
        self,
        contact_id: str,
        limit: int = 50
    ) -> list[Event]:
        """Get timeline for a contact."""
        events, _ = await self.list_events(contact_id=contact_id, limit=limit)
        return events
    
    async def get_deal_timeline(
        self,
        deal_id: str,
        limit: int = 50
    ) -> list[Event]:
        """Get timeline for a deal."""
        events, _ = await self.list_events(deal_id=deal_id, limit=limit)
        return events
    
    async def get_account_timeline(
        self,
        account_id: str,
        limit: int = 50
    ) -> list[Event]:
        """Get timeline for an account."""
        events, _ = await self.list_events(account_id=account_id, limit=limit)
        return events
    
    async def get_user_activity(
        self,
        user_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list[Event]:
        """Get activity for a user."""
        events, _ = await self.list_events(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit
        )
        return events
    
    # Activity feed
    async def create_feed(
        self,
        name: str,
        **kwargs
    ) -> ActivityFeed:
        """Create an activity feed."""
        feed = ActivityFeed(
            id=str(uuid.uuid4()),
            name=name,
            **kwargs
        )
        
        self.feeds[feed.id] = feed
        return feed
    
    async def get_feed_events(
        self,
        feed_id: str,
        limit: int = 50
    ) -> list[Event]:
        """Get events for an activity feed."""
        feed = self.feeds.get(feed_id)
        if not feed:
            return []
        
        events, _ = await self.list_events(
            contact_id=feed.contact_id,
            account_id=feed.account_id,
            deal_id=feed.deal_id,
            user_id=feed.user_id,
            event_types=feed.event_types if feed.event_types else None,
            categories=feed.categories if feed.categories else None,
            from_date=feed.from_date,
            to_date=feed.to_date,
            limit=limit
        )
        
        return events
    
    # Analytics
    async def get_event_counts(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        group_by: str = "type"  # type, category, user
    ) -> dict[str, int]:
        """Get event counts grouped by dimension."""
        events = list(self.events.values())
        
        if from_date:
            events = [e for e in events if e.occurred_at >= from_date]
        if to_date:
            events = [e for e in events if e.occurred_at <= to_date]
        
        counts: dict[str, int] = {}
        
        for event in events:
            if group_by == "type":
                key = event.event_type.value
            elif group_by == "category":
                key = event.category.value
            elif group_by == "user":
                key = event.user_id or "unknown"
            else:
                key = "total"
            
            counts[key] = counts.get(key, 0) + 1
        
        return counts
    
    async def get_daily_activity(
        self,
        days: int = 30,
        user_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get daily activity summary."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        events, _ = await self.list_events(
            user_id=user_id,
            from_date=start_date,
            to_date=end_date,
            limit=10000
        )
        
        # Group by date
        daily: dict[str, int] = {}
        for i in range(days):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily[date] = 0
        
        for event in events:
            date = event.occurred_at.strftime("%Y-%m-%d")
            if date in daily:
                daily[date] += 1
        
        return [
            {"date": date, "count": count}
            for date, count in sorted(daily.items())
        ]
    
    async def get_engagement_score(
        self,
        contact_id: str,
        days: int = 30
    ) -> dict[str, Any]:
        """Calculate engagement score for a contact."""
        from_date = datetime.utcnow() - timedelta(days=days)
        
        events, _ = await self.list_events(
            contact_id=contact_id,
            from_date=from_date,
            limit=1000
        )
        
        # Score weights
        weights = {
            EventType.EMAIL_REPLIED: 10,
            EventType.MEETING_COMPLETED: 15,
            EventType.DOCUMENT_VIEWED: 5,
            EventType.DOCUMENT_SIGNED: 20,
            EventType.QUOTE_VIEWED: 5,
            EventType.QUOTE_ACCEPTED: 25,
            EventType.EMAIL_OPENED: 2,
            EventType.EMAIL_CLICKED: 3,
            EventType.PAGE_VIEWED: 1,
            EventType.FORM_SUBMITTED: 8,
        }
        
        score = 0
        activity_by_type: dict[str, int] = {}
        
        for event in events:
            weight = weights.get(event.event_type, 1)
            score += weight
            
            type_key = event.event_type.value
            activity_by_type[type_key] = activity_by_type.get(type_key, 0) + 1
        
        return {
            "contact_id": contact_id,
            "score": score,
            "total_activities": len(events),
            "activity_breakdown": activity_by_type,
            "period_days": days,
            "last_activity": events[0].occurred_at.isoformat() if events else None,
        }
    
    # Convenience logging methods
    async def log_email_sent(
        self,
        contact_id: str,
        subject: str,
        user_id: Optional[str] = None,
        email_id: Optional[str] = None,
        **kwargs
    ) -> Event:
        """Log an email sent event."""
        return await self.log_event(
            event_type=EventType.EMAIL_SENT,
            title=f"Email sent: {subject}",
            contact_id=contact_id,
            user_id=user_id,
            object_type="email",
            object_id=email_id,
            metadata={"subject": subject, **kwargs}
        )
    
    async def log_email_opened(
        self,
        contact_id: str,
        subject: str,
        email_id: Optional[str] = None,
        **kwargs
    ) -> Event:
        """Log an email opened event."""
        return await self.log_event(
            event_type=EventType.EMAIL_OPENED,
            title=f"Email opened: {subject}",
            contact_id=contact_id,
            object_type="email",
            object_id=email_id,
            metadata={"subject": subject, **kwargs}
        )
    
    async def log_call(
        self,
        contact_id: str,
        direction: str,  # outbound, inbound, missed
        duration_seconds: int = 0,
        user_id: Optional[str] = None,
        call_id: Optional[str] = None,
        **kwargs
    ) -> Event:
        """Log a call event."""
        type_map = {
            "outbound": EventType.CALL_MADE,
            "inbound": EventType.CALL_RECEIVED,
            "missed": EventType.CALL_MISSED,
        }
        event_type = type_map.get(direction, EventType.CALL_MADE)
        
        title = f"Call ({direction})"
        if duration_seconds > 0:
            minutes = duration_seconds // 60
            title += f" - {minutes}m"
        
        return await self.log_event(
            event_type=event_type,
            title=title,
            contact_id=contact_id,
            user_id=user_id,
            object_type="call",
            object_id=call_id,
            duration_seconds=duration_seconds,
            metadata={"direction": direction, **kwargs}
        )
    
    async def log_meeting(
        self,
        contact_id: str,
        title: str,
        status: str,  # scheduled, completed, cancelled, no_show
        user_id: Optional[str] = None,
        meeting_id: Optional[str] = None,
        **kwargs
    ) -> Event:
        """Log a meeting event."""
        type_map = {
            "scheduled": EventType.MEETING_SCHEDULED,
            "completed": EventType.MEETING_COMPLETED,
            "cancelled": EventType.MEETING_CANCELLED,
            "no_show": EventType.MEETING_NO_SHOW,
        }
        event_type = type_map.get(status, EventType.MEETING_SCHEDULED)
        
        return await self.log_event(
            event_type=event_type,
            title=f"Meeting {status}: {title}",
            contact_id=contact_id,
            user_id=user_id,
            object_type="meeting",
            object_id=meeting_id,
            metadata={"meeting_title": title, "status": status, **kwargs}
        )
    
    async def log_deal_stage_change(
        self,
        deal_id: str,
        from_stage: str,
        to_stage: str,
        contact_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Event:
        """Log a deal stage change."""
        return await self.log_event(
            event_type=EventType.DEAL_STAGE_CHANGED,
            title=f"Deal moved from {from_stage} to {to_stage}",
            deal_id=deal_id,
            contact_id=contact_id,
            user_id=user_id,
            object_type="deal",
            object_id=deal_id,
            metadata={"from_stage": from_stage, "to_stage": to_stage, **kwargs}
        )


# Singleton instance
_event_service: Optional[EventService] = None


def get_event_service() -> EventService:
    """Get event service singleton."""
    global _event_service
    if _event_service is None:
        _event_service = EventService()
    return _event_service
