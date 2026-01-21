"""
Activity Feed Service
=====================
Real-time activity feed, notifications, and social features.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid


class ActivityType(str, Enum):
    """Activity types."""
    # Lead activities
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_ASSIGNED = "lead_assigned"
    LEAD_CONVERTED = "lead_converted"
    LEAD_QUALIFIED = "lead_qualified"
    
    # Contact activities
    CONTACT_CREATED = "contact_created"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_MERGED = "contact_merged"
    
    # Company activities
    COMPANY_CREATED = "company_created"
    COMPANY_UPDATED = "company_updated"
    
    # Deal activities
    DEAL_CREATED = "deal_created"
    DEAL_UPDATED = "deal_updated"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    DEAL_ASSIGNED = "deal_assigned"
    
    # Communication activities
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    CALL_MADE = "call_made"
    CALL_RECEIVED = "call_received"
    CALL_COMPLETED = "call_completed"
    SMS_SENT = "sms_sent"
    SMS_RECEIVED = "sms_received"
    
    # Meeting activities
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_STARTED = "meeting_started"
    MEETING_COMPLETED = "meeting_completed"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_RESCHEDULED = "meeting_rescheduled"
    
    # Task activities
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_ASSIGNED = "task_assigned"
    TASK_OVERDUE = "task_overdue"
    
    # Note activities
    NOTE_CREATED = "note_created"
    NOTE_MENTIONED = "note_mentioned"
    
    # Document activities
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_SHARED = "document_shared"
    DOCUMENT_VIEWED = "document_viewed"
    
    # Quote activities
    QUOTE_CREATED = "quote_created"
    QUOTE_SENT = "quote_sent"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    
    # Contract activities
    CONTRACT_CREATED = "contract_created"
    CONTRACT_SENT = "contract_sent"
    CONTRACT_SIGNED = "contract_signed"
    
    # Campaign activities
    CAMPAIGN_STARTED = "campaign_started"
    CAMPAIGN_COMPLETED = "campaign_completed"
    SEQUENCE_ENROLLED = "sequence_enrolled"
    SEQUENCE_COMPLETED = "sequence_completed"
    
    # Team activities
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    COMMENT_ADDED = "comment_added"
    MENTION_CREATED = "mention_created"
    
    # Achievement activities
    BADGE_EARNED = "badge_earned"
    MILESTONE_REACHED = "milestone_reached"
    GOAL_ACHIEVED = "goal_achieved"
    
    # System activities
    INTEGRATION_CONNECTED = "integration_connected"
    IMPORT_COMPLETED = "import_completed"
    EXPORT_COMPLETED = "export_completed"


class ActorType(str, Enum):
    """Actor types."""
    USER = "user"
    SYSTEM = "system"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    API = "api"


class TargetType(str, Enum):
    """Target entity types."""
    LEAD = "lead"
    CONTACT = "contact"
    COMPANY = "company"
    DEAL = "deal"
    TASK = "task"
    MEETING = "meeting"
    CALL = "call"
    EMAIL = "email"
    NOTE = "note"
    DOCUMENT = "document"
    QUOTE = "quote"
    CONTRACT = "contract"
    CAMPAIGN = "campaign"
    SEQUENCE = "sequence"
    TEAM = "team"
    USER = "user"


@dataclass
class ActivityActor:
    """Actor who performed the activity."""
    id: str
    type: ActorType
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass
class ActivityTarget:
    """Target of the activity."""
    id: str
    type: TargetType
    name: str
    url: Optional[str] = None


@dataclass
class ActivityMention:
    """Mention in an activity."""
    user_id: str
    user_name: str
    start_index: int
    end_index: int


@dataclass
class Activity:
    """Activity feed item."""
    id: str
    type: ActivityType
    actor: ActivityActor
    target: ActivityTarget
    org_id: str
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    secondary_targets: list[ActivityTarget] = field(default_factory=list)
    mentions: list[ActivityMention] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_important: bool = False
    is_read: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None


@dataclass
class ActivityFilter:
    """Filter for activity feed queries."""
    activity_types: Optional[list[ActivityType]] = None
    actor_ids: Optional[list[str]] = None
    target_types: Optional[list[TargetType]] = None
    target_ids: Optional[list[str]] = None
    is_important: Optional[bool] = None
    is_read: Optional[bool] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None


@dataclass
class FeedSubscription:
    """Subscription to activity feed."""
    id: str
    user_id: str
    entity_type: TargetType
    entity_id: str
    notify_on_activity: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UnreadCount:
    """Unread activity counts."""
    total: int = 0
    important: int = 0
    mentions: int = 0
    by_type: dict[str, int] = field(default_factory=dict)


class ActivityFeedService:
    """
    Activity Feed service.
    
    Provides real-time activity feed, notifications, subscriptions,
    and social features like mentions and comments.
    """
    
    def __init__(self):
        """Initialize activity feed service."""
        self.activities: dict[str, Activity] = {}
        self.subscriptions: dict[str, FeedSubscription] = {}
        self.user_reads: dict[str, dict[str, datetime]] = {}  # user_id -> activity_id -> read_at
    
    async def create_activity(
        self,
        activity_type: ActivityType,
        actor: ActivityActor,
        target: ActivityTarget,
        org_id: str,
        description: str,
        details: Optional[dict[str, Any]] = None,
        secondary_targets: Optional[list[ActivityTarget]] = None,
        mentions: Optional[list[ActivityMention]] = None,
        is_important: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Activity:
        """Create a new activity."""
        activity = Activity(
            id=str(uuid.uuid4()),
            type=activity_type,
            actor=actor,
            target=target,
            org_id=org_id,
            description=description,
            details=details or {},
            secondary_targets=secondary_targets or [],
            mentions=mentions or [],
            is_important=is_important,
            metadata=metadata or {},
        )
        
        self.activities[activity.id] = activity
        return activity
    
    async def log_activity(
        self,
        activity_type: ActivityType,
        actor_id: str,
        actor_name: str,
        target_type: TargetType,
        target_id: str,
        target_name: str,
        org_id: str,
        description: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        is_important: bool = False,
    ) -> Activity:
        """Convenience method to log an activity."""
        actor = ActivityActor(
            id=actor_id,
            type=ActorType.USER,
            name=actor_name,
        )
        
        target = ActivityTarget(
            id=target_id,
            type=target_type,
            name=target_name,
        )
        
        if not description:
            description = self._generate_description(activity_type, actor, target)
        
        return await self.create_activity(
            activity_type=activity_type,
            actor=actor,
            target=target,
            org_id=org_id,
            description=description,
            details=details,
            is_important=is_important,
        )
    
    def _generate_description(
        self,
        activity_type: ActivityType,
        actor: ActivityActor,
        target: ActivityTarget,
    ) -> str:
        """Generate activity description."""
        templates = {
            ActivityType.LEAD_CREATED: "{actor} created lead {target}",
            ActivityType.LEAD_UPDATED: "{actor} updated lead {target}",
            ActivityType.LEAD_ASSIGNED: "{actor} assigned lead {target}",
            ActivityType.LEAD_CONVERTED: "{actor} converted lead {target}",
            ActivityType.DEAL_CREATED: "{actor} created deal {target}",
            ActivityType.DEAL_WON: "{actor} won deal {target}",
            ActivityType.DEAL_LOST: "{actor} lost deal {target}",
            ActivityType.DEAL_STAGE_CHANGED: "{actor} moved deal {target} to new stage",
            ActivityType.EMAIL_SENT: "{actor} sent email to {target}",
            ActivityType.EMAIL_OPENED: "{target} opened email",
            ActivityType.CALL_MADE: "{actor} called {target}",
            ActivityType.MEETING_SCHEDULED: "{actor} scheduled meeting with {target}",
            ActivityType.TASK_COMPLETED: "{actor} completed task {target}",
            ActivityType.NOTE_CREATED: "{actor} added note to {target}",
            ActivityType.DOCUMENT_UPLOADED: "{actor} uploaded document {target}",
            ActivityType.QUOTE_SENT: "{actor} sent quote {target}",
            ActivityType.CONTRACT_SIGNED: "{target} signed contract",
            ActivityType.BADGE_EARNED: "{actor} earned badge {target}",
        }
        
        template = templates.get(activity_type, "{actor} performed action on {target}")
        return template.format(actor=actor.name, target=target.name)
    
    async def get_activity(self, activity_id: str) -> Optional[Activity]:
        """Get an activity by ID."""
        return self.activities.get(activity_id)
    
    async def get_feed(
        self,
        org_id: str,
        user_id: Optional[str] = None,
        filters: Optional[ActivityFilter] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Activity]:
        """Get activity feed."""
        activities = [a for a in self.activities.values() if a.org_id == org_id]
        
        if filters:
            activities = self._apply_filters(activities, filters)
        
        # Sort by created_at descending
        activities.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply read status for user
        if user_id:
            user_reads = self.user_reads.get(user_id, {})
            for activity in activities:
                if activity.id in user_reads:
                    activity.is_read = True
                    activity.read_at = user_reads[activity.id]
        
        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        
        return activities[start:end]
    
    def _apply_filters(
        self,
        activities: list[Activity],
        filters: ActivityFilter,
    ) -> list[Activity]:
        """Apply filters to activities."""
        if filters.activity_types:
            activities = [a for a in activities if a.type in filters.activity_types]
        
        if filters.actor_ids:
            activities = [a for a in activities if a.actor.id in filters.actor_ids]
        
        if filters.target_types:
            activities = [a for a in activities if a.target.type in filters.target_types]
        
        if filters.target_ids:
            activities = [a for a in activities if a.target.id in filters.target_ids]
        
        if filters.is_important is not None:
            activities = [a for a in activities if a.is_important == filters.is_important]
        
        if filters.since:
            activities = [a for a in activities if a.created_at >= filters.since]
        
        if filters.until:
            activities = [a for a in activities if a.created_at <= filters.until]
        
        return activities
    
    async def get_entity_timeline(
        self,
        entity_type: TargetType,
        entity_id: str,
        limit: int = 100,
    ) -> list[Activity]:
        """Get activity timeline for an entity."""
        activities = [
            a for a in self.activities.values()
            if (a.target.type == entity_type and a.target.id == entity_id)
            or any(t.type == entity_type and t.id == entity_id for t in a.secondary_targets)
        ]
        
        activities.sort(key=lambda x: x.created_at, reverse=True)
        return activities[:limit]
    
    async def get_user_activity(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[Activity]:
        """Get activities by a specific user."""
        activities = [
            a for a in self.activities.values()
            if a.actor.id == user_id
        ]
        
        activities.sort(key=lambda x: x.created_at, reverse=True)
        return activities[:limit]
    
    async def get_mentions(
        self,
        user_id: str,
        include_read: bool = False,
    ) -> list[Activity]:
        """Get activities where user was mentioned."""
        user_reads = self.user_reads.get(user_id, {})
        
        activities = [
            a for a in self.activities.values()
            if any(m.user_id == user_id for m in a.mentions)
        ]
        
        if not include_read:
            activities = [a for a in activities if a.id not in user_reads]
        
        activities.sort(key=lambda x: x.created_at, reverse=True)
        return activities
    
    async def mark_as_read(
        self,
        user_id: str,
        activity_ids: list[str],
    ):
        """Mark activities as read for a user."""
        if user_id not in self.user_reads:
            self.user_reads[user_id] = {}
        
        now = datetime.utcnow()
        for activity_id in activity_ids:
            self.user_reads[user_id][activity_id] = now
    
    async def mark_all_as_read(
        self,
        user_id: str,
        org_id: str,
    ):
        """Mark all activities as read for a user."""
        if user_id not in self.user_reads:
            self.user_reads[user_id] = {}
        
        now = datetime.utcnow()
        for activity in self.activities.values():
            if activity.org_id == org_id:
                self.user_reads[user_id][activity.id] = now
    
    async def get_unread_count(
        self,
        user_id: str,
        org_id: str,
    ) -> UnreadCount:
        """Get unread activity counts for a user."""
        user_reads = self.user_reads.get(user_id, {})
        
        unread = [
            a for a in self.activities.values()
            if a.org_id == org_id and a.id not in user_reads
        ]
        
        by_type: dict[str, int] = {}
        for activity in unread:
            type_name = activity.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        important = len([a for a in unread if a.is_important])
        mentions = len([
            a for a in unread
            if any(m.user_id == user_id for m in a.mentions)
        ])
        
        return UnreadCount(
            total=len(unread),
            important=important,
            mentions=mentions,
            by_type=by_type,
        )
    
    async def subscribe(
        self,
        user_id: str,
        entity_type: TargetType,
        entity_id: str,
        notify_on_activity: bool = True,
    ) -> FeedSubscription:
        """Subscribe to an entity's activity."""
        sub = FeedSubscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            notify_on_activity=notify_on_activity,
        )
        self.subscriptions[sub.id] = sub
        return sub
    
    async def unsubscribe(
        self,
        user_id: str,
        entity_type: TargetType,
        entity_id: str,
    ) -> bool:
        """Unsubscribe from an entity's activity."""
        for sub_id, sub in list(self.subscriptions.items()):
            if (sub.user_id == user_id and 
                sub.entity_type == entity_type and 
                sub.entity_id == entity_id):
                del self.subscriptions[sub_id]
                return True
        return False
    
    async def get_subscriptions(
        self,
        user_id: str,
    ) -> list[FeedSubscription]:
        """Get user's subscriptions."""
        return [s for s in self.subscriptions.values() if s.user_id == user_id]
    
    async def get_subscribers(
        self,
        entity_type: TargetType,
        entity_id: str,
    ) -> list[str]:
        """Get users subscribed to an entity."""
        return [
            s.user_id for s in self.subscriptions.values()
            if s.entity_type == entity_type and s.entity_id == entity_id
        ]
    
    async def get_activity_stats(
        self,
        org_id: str,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get activity statistics."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        activities = [
            a for a in self.activities.values()
            if a.org_id == org_id and a.created_at >= since
        ]
        
        by_type: dict[str, int] = {}
        by_actor: dict[str, int] = {}
        by_day: dict[str, int] = {}
        
        for activity in activities:
            # By type
            type_name = activity.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # By actor
            by_actor[activity.actor.id] = by_actor.get(activity.actor.id, 0) + 1
            
            # By day
            day = activity.created_at.strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
        
        return {
            "total_activities": len(activities),
            "by_type": by_type,
            "by_actor": by_actor,
            "by_day": by_day,
            "most_active_users": sorted(by_actor.items(), key=lambda x: -x[1])[:10],
            "top_activity_types": sorted(by_type.items(), key=lambda x: -x[1])[:10],
        }
    
    async def delete_old_activities(
        self,
        org_id: str,
        older_than_days: int = 90,
    ) -> int:
        """Delete old activities."""
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        
        to_delete = [
            a.id for a in self.activities.values()
            if a.org_id == org_id and a.created_at < cutoff
        ]
        
        for activity_id in to_delete:
            del self.activities[activity_id]
        
        return len(to_delete)


# Singleton instance
_activity_feed_service: Optional[ActivityFeedService] = None


def get_activity_feed_service() -> ActivityFeedService:
    """Get or create activity feed service singleton."""
    global _activity_feed_service
    if _activity_feed_service is None:
        _activity_feed_service = ActivityFeedService()
    return _activity_feed_service
