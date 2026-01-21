"""
Notification Preferences Service - User Notification Settings
===============================================================
Handles user notification preferences, channels, and delivery settings.
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any, Optional
import uuid


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"


class NotificationType(str, Enum):
    """Types of notifications."""
    # Deals
    DEAL_ASSIGNED = "deal_assigned"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    DEAL_CLOSE_DATE_APPROACHING = "deal_close_date_approaching"
    DEAL_OVERDUE = "deal_overdue"
    
    # Tasks
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    TASK_COMPLETED = "task_completed"
    
    # Meetings
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_REMINDER = "meeting_reminder"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_RESCHEDULED = "meeting_rescheduled"
    
    # Email engagement
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    EMAIL_BOUNCED = "email_bounced"
    
    # Leads/Contacts
    LEAD_ASSIGNED = "lead_assigned"
    CONTACT_ACTIVITY = "contact_activity"
    CONTACT_SCORE_CHANGED = "contact_score_changed"
    HOT_LEAD = "hot_lead"
    
    # Quotes/Proposals
    QUOTE_VIEWED = "quote_viewed"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    QUOTE_EXPIRED = "quote_expired"
    
    # Approvals
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    
    # Team
    TEAM_MENTION = "team_mention"
    TEAM_COMMENT = "team_comment"
    TEAM_ANNOUNCEMENT = "team_announcement"
    
    # Goals
    GOAL_ACHIEVED = "goal_achieved"
    GOAL_AT_RISK = "goal_at_risk"
    GOAL_PROGRESS = "goal_progress"
    
    # System
    SYSTEM_ALERT = "system_alert"
    INTEGRATION_ERROR = "integration_error"
    IMPORT_COMPLETED = "import_completed"
    EXPORT_COMPLETED = "export_completed"
    REPORT_READY = "report_ready"


class Frequency(str, Enum):
    """Notification frequency."""
    INSTANT = "instant"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


@dataclass
class ChannelSettings:
    """Settings for a notification channel."""
    channel: NotificationChannel
    enabled: bool = True
    address: Optional[str] = None  # email, phone, webhook URL, etc.
    verified: bool = False
    verified_at: Optional[datetime] = None
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuietHours:
    """Quiet hours configuration."""
    enabled: bool = False
    start_time: Optional[time] = None  # e.g., 22:00
    end_time: Optional[time] = None    # e.g., 08:00
    timezone: str = "UTC"
    days: list[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    exceptions: list[str] = field(default_factory=list)  # Types to always send


@dataclass
class DigestSettings:
    """Digest notification settings."""
    enabled: bool = False
    frequency: Frequency = Frequency.DAILY
    send_time: Optional[time] = None
    timezone: str = "UTC"
    include_types: list[NotificationType] = field(default_factory=list)


@dataclass
class NotificationPreference:
    """User notification preference for a specific type."""
    id: str
    user_id: str
    notification_type: NotificationType
    channels: dict[NotificationChannel, bool] = field(default_factory=dict)
    frequency: Frequency = Frequency.INSTANT
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)  # e.g., {"deal_amount_min": 10000}
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserNotificationSettings:
    """Complete notification settings for a user."""
    user_id: str
    global_enabled: bool = True
    channels: list[ChannelSettings] = field(default_factory=list)
    quiet_hours: QuietHours = field(default_factory=QuietHours)
    digest: DigestSettings = field(default_factory=DigestSettings)
    preferences: dict[NotificationType, NotificationPreference] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class NotificationPrefsService:
    """Service for managing notification preferences."""
    
    def __init__(self):
        """Initialize notification preferences service."""
        self.user_settings: dict[str, UserNotificationSettings] = {}
        self._default_channels = [
            NotificationChannel.EMAIL,
            NotificationChannel.IN_APP,
        ]
    
    async def get_user_settings(
        self,
        user_id: str,
        create_if_missing: bool = True
    ) -> Optional[UserNotificationSettings]:
        """Get notification settings for a user."""
        settings = self.user_settings.get(user_id)
        
        if not settings and create_if_missing:
            settings = await self._create_default_settings(user_id)
        
        return settings
    
    async def _create_default_settings(
        self,
        user_id: str
    ) -> UserNotificationSettings:
        """Create default notification settings for a user."""
        # Default channel settings
        channels = [
            ChannelSettings(
                channel=NotificationChannel.EMAIL,
                enabled=True,
            ),
            ChannelSettings(
                channel=NotificationChannel.IN_APP,
                enabled=True,
            ),
        ]
        
        # Default preferences for all notification types
        preferences = {}
        for ntype in NotificationType:
            pref_id = str(uuid.uuid4())
            preferences[ntype] = NotificationPreference(
                id=pref_id,
                user_id=user_id,
                notification_type=ntype,
                channels={
                    NotificationChannel.EMAIL: True,
                    NotificationChannel.IN_APP: True,
                },
                enabled=True,
            )
        
        settings = UserNotificationSettings(
            user_id=user_id,
            channels=channels,
            preferences=preferences,
        )
        
        self.user_settings[user_id] = settings
        return settings
    
    async def update_global_settings(
        self,
        user_id: str,
        global_enabled: Optional[bool] = None,
        quiet_hours: Optional[dict[str, Any]] = None,
        digest: Optional[dict[str, Any]] = None,
    ) -> UserNotificationSettings:
        """Update global notification settings."""
        settings = await self.get_user_settings(user_id)
        
        if global_enabled is not None:
            settings.global_enabled = global_enabled
        
        if quiet_hours:
            settings.quiet_hours.enabled = quiet_hours.get("enabled", settings.quiet_hours.enabled)
            if "start_time" in quiet_hours:
                h, m = map(int, quiet_hours["start_time"].split(":"))
                settings.quiet_hours.start_time = time(h, m)
            if "end_time" in quiet_hours:
                h, m = map(int, quiet_hours["end_time"].split(":"))
                settings.quiet_hours.end_time = time(h, m)
            settings.quiet_hours.timezone = quiet_hours.get("timezone", settings.quiet_hours.timezone)
            settings.quiet_hours.days = quiet_hours.get("days", settings.quiet_hours.days)
        
        if digest:
            settings.digest.enabled = digest.get("enabled", settings.digest.enabled)
            if "frequency" in digest:
                settings.digest.frequency = Frequency(digest["frequency"])
            if "send_time" in digest:
                h, m = map(int, digest["send_time"].split(":"))
                settings.digest.send_time = time(h, m)
            settings.digest.timezone = digest.get("timezone", settings.digest.timezone)
        
        settings.updated_at = datetime.utcnow()
        return settings
    
    async def update_channel(
        self,
        user_id: str,
        channel: NotificationChannel,
        enabled: Optional[bool] = None,
        address: Optional[str] = None,
        channel_settings: Optional[dict[str, Any]] = None,
    ) -> ChannelSettings:
        """Update a notification channel."""
        settings = await self.get_user_settings(user_id)
        
        # Find or create channel settings
        channel_config = None
        for cs in settings.channels:
            if cs.channel == channel:
                channel_config = cs
                break
        
        if not channel_config:
            channel_config = ChannelSettings(channel=channel)
            settings.channels.append(channel_config)
        
        if enabled is not None:
            channel_config.enabled = enabled
        if address is not None:
            channel_config.address = address
            channel_config.verified = False  # Require re-verification
        if channel_settings:
            channel_config.settings.update(channel_settings)
        
        settings.updated_at = datetime.utcnow()
        return channel_config
    
    async def verify_channel(
        self,
        user_id: str,
        channel: NotificationChannel,
        verification_code: str
    ) -> bool:
        """Verify a notification channel."""
        settings = await self.get_user_settings(user_id, create_if_missing=False)
        if not settings:
            return False
        
        for cs in settings.channels:
            if cs.channel == channel:
                # In production, verify against stored code
                cs.verified = True
                cs.verified_at = datetime.utcnow()
                settings.updated_at = datetime.utcnow()
                return True
        
        return False
    
    async def update_preference(
        self,
        user_id: str,
        notification_type: NotificationType,
        enabled: Optional[bool] = None,
        channels: Optional[dict[str, bool]] = None,
        frequency: Optional[Frequency] = None,
        conditions: Optional[dict[str, Any]] = None,
    ) -> NotificationPreference:
        """Update preference for a notification type."""
        settings = await self.get_user_settings(user_id)
        
        if notification_type not in settings.preferences:
            settings.preferences[notification_type] = NotificationPreference(
                id=str(uuid.uuid4()),
                user_id=user_id,
                notification_type=notification_type,
            )
        
        pref = settings.preferences[notification_type]
        
        if enabled is not None:
            pref.enabled = enabled
        if channels:
            for ch_name, ch_enabled in channels.items():
                try:
                    ch = NotificationChannel(ch_name)
                    pref.channels[ch] = ch_enabled
                except ValueError:
                    pass
        if frequency:
            pref.frequency = frequency
        if conditions is not None:
            pref.conditions = conditions
        
        pref.updated_at = datetime.utcnow()
        settings.updated_at = datetime.utcnow()
        
        return pref
    
    async def bulk_update_preferences(
        self,
        user_id: str,
        updates: list[dict[str, Any]]
    ) -> int:
        """Bulk update multiple preferences."""
        updated = 0
        
        for update in updates:
            try:
                ntype = NotificationType(update.get("notification_type"))
                frequency = None
                if "frequency" in update:
                    frequency = Frequency(update["frequency"])
                
                await self.update_preference(
                    user_id=user_id,
                    notification_type=ntype,
                    enabled=update.get("enabled"),
                    channels=update.get("channels"),
                    frequency=frequency,
                    conditions=update.get("conditions"),
                )
                updated += 1
            except (ValueError, KeyError):
                continue
        
        return updated
    
    async def get_preference(
        self,
        user_id: str,
        notification_type: NotificationType
    ) -> Optional[NotificationPreference]:
        """Get preference for a specific notification type."""
        settings = await self.get_user_settings(user_id, create_if_missing=False)
        if not settings:
            return None
        
        return settings.preferences.get(notification_type)
    
    async def should_notify(
        self,
        user_id: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        context: Optional[dict[str, Any]] = None
    ) -> bool:
        """Check if a user should receive a notification."""
        settings = await self.get_user_settings(user_id, create_if_missing=False)
        if not settings:
            return True  # Default to notify
        
        # Check global enabled
        if not settings.global_enabled:
            return False
        
        # Check quiet hours
        if settings.quiet_hours.enabled and await self._is_quiet_hours(settings.quiet_hours):
            if notification_type.value not in settings.quiet_hours.exceptions:
                return False
        
        # Check channel enabled
        channel_enabled = False
        for cs in settings.channels:
            if cs.channel == channel and cs.enabled:
                channel_enabled = True
                break
        if not channel_enabled:
            return False
        
        # Check specific preference
        pref = settings.preferences.get(notification_type)
        if pref:
            if not pref.enabled:
                return False
            if channel in pref.channels and not pref.channels[channel]:
                return False
            
            # Check conditions
            if pref.conditions and context:
                for key, value in pref.conditions.items():
                    context_value = context.get(key)
                    if key.endswith("_min") and context_value is not None:
                        if context_value < value:
                            return False
                    elif key.endswith("_max") and context_value is not None:
                        if context_value > value:
                            return False
        
        return True
    
    async def _is_quiet_hours(self, quiet_hours: QuietHours) -> bool:
        """Check if currently in quiet hours."""
        if not quiet_hours.enabled:
            return False
        
        # In production, use proper timezone handling
        now = datetime.utcnow().time()
        
        if quiet_hours.start_time and quiet_hours.end_time:
            if quiet_hours.start_time > quiet_hours.end_time:
                # Overnight quiet hours (e.g., 22:00 to 08:00)
                return now >= quiet_hours.start_time or now <= quiet_hours.end_time
            else:
                return quiet_hours.start_time <= now <= quiet_hours.end_time
        
        return False
    
    async def get_delivery_channels(
        self,
        user_id: str,
        notification_type: NotificationType
    ) -> list[NotificationChannel]:
        """Get enabled channels for a notification type."""
        settings = await self.get_user_settings(user_id, create_if_missing=False)
        if not settings:
            return self._default_channels
        
        channels = []
        pref = settings.preferences.get(notification_type)
        
        for cs in settings.channels:
            if not cs.enabled:
                continue
            
            # Check type-specific preference
            if pref and cs.channel in pref.channels:
                if pref.channels[cs.channel]:
                    channels.append(cs.channel)
            else:
                # Default to channel being enabled for this type
                channels.append(cs.channel)
        
        return channels
    
    async def reset_to_defaults(self, user_id: str) -> UserNotificationSettings:
        """Reset user settings to defaults."""
        if user_id in self.user_settings:
            del self.user_settings[user_id]
        
        return await self.get_user_settings(user_id)


# Singleton instance
_notification_prefs_service: Optional[NotificationPrefsService] = None


def get_notification_prefs_service() -> NotificationPrefsService:
    """Get notification preferences service singleton."""
    global _notification_prefs_service
    if _notification_prefs_service is None:
        _notification_prefs_service = NotificationPrefsService()
    return _notification_prefs_service
