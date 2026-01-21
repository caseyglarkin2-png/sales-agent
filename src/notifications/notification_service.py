"""
Notification System.

Handles alerts, daily summaries, and notifications via various channels.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    REPLY_RECEIVED = "reply_received"
    MEETING_BOOKED = "meeting_booked"
    HIGH_VALUE_ENGAGEMENT = "high_value_engagement"
    SEQUENCE_COMPLETED = "sequence_completed"
    DRAFT_EXPIRED = "draft_expired"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    ALERT = "alert"
    REMINDER = "reminder"


class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """A notification."""
    id: str
    type: NotificationType
    title: str
    message: str
    priority: NotificationPriority
    channel: NotificationChannel
    
    # Metadata
    data: Optional[Dict[str, Any]] = None
    link: Optional[str] = None
    
    # Status
    created_at: datetime = None
    read_at: Optional[datetime] = None
    sent_via: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.sent_via is None:
            self.sent_via = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "channel": self.channel.value,
            "data": self.data,
            "link": self.link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "read": self.read_at is not None,
        }


class NotificationService:
    """Manages notifications and alerts."""
    
    def __init__(self):
        self.notifications: List[Notification] = []
        self.notification_settings = {
            "email_enabled": True,
            "slack_enabled": False,
            "slack_webhook": None,
            "daily_summary_time": "09:00",
            "quiet_hours_start": 22,
            "quiet_hours_end": 7,
        }
    
    def create_notification(
        self,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        data: Optional[Dict[str, Any]] = None,
        link: Optional[str] = None,
    ) -> Notification:
        """Create a new notification.
        
        Args:
            type: Notification type
            title: Notification title
            message: Notification message
            priority: Priority level
            channel: Delivery channel
            data: Additional data
            link: Action link
            
        Returns:
            Created notification
        """
        notification = Notification(
            id=f"notif_{uuid.uuid4().hex[:8]}",
            type=type,
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            data=data,
            link=link,
        )
        
        self.notifications.append(notification)
        logger.info(f"Created notification: {title} ({type.value})")
        
        # Auto-send if not in-app only
        if channel != NotificationChannel.IN_APP:
            self._send_notification(notification)
        
        return notification
    
    def _send_notification(self, notification: Notification):
        """Send notification via configured channel."""
        if notification.channel == NotificationChannel.EMAIL:
            self._send_email(notification)
        elif notification.channel == NotificationChannel.SLACK:
            self._send_slack(notification)
    
    def _send_email(self, notification: Notification):
        """Send email notification."""
        # Would integrate with Gmail connector
        logger.info(f"Would send email notification: {notification.title}")
        notification.sent_via.append("email")
    
    def _send_slack(self, notification: Notification):
        """Send Slack notification."""
        webhook = self.notification_settings.get("slack_webhook")
        if not webhook:
            logger.warning("Slack webhook not configured")
            return
        
        # Would send to Slack
        logger.info(f"Would send Slack notification: {notification.title}")
        notification.sent_via.append("slack")
    
    def notify_reply_received(
        self,
        contact_name: str,
        contact_email: str,
        company: str,
        subject: str,
    ) -> Notification:
        """Create notification for received reply."""
        return self.create_notification(
            type=NotificationType.REPLY_RECEIVED,
            title=f"Reply from {contact_name}",
            message=f"{contact_name} at {company} replied to: {subject}",
            priority=NotificationPriority.HIGH,
            data={
                "contact_email": contact_email,
                "company": company,
                "subject": subject,
            },
            link=f"/inbox?email={contact_email}",
        )
    
    def notify_meeting_booked(
        self,
        contact_name: str,
        company: str,
        meeting_time: datetime,
    ) -> Notification:
        """Create notification for booked meeting."""
        return self.create_notification(
            type=NotificationType.MEETING_BOOKED,
            title=f"Meeting booked with {contact_name}",
            message=f"Meeting with {contact_name} at {company} scheduled for {meeting_time.strftime('%B %d at %I:%M %p')}",
            priority=NotificationPriority.HIGH,
            data={
                "contact_name": contact_name,
                "company": company,
                "meeting_time": meeting_time.isoformat(),
            },
        )
    
    def notify_sequence_completed(
        self,
        contact_name: str,
        sequence_name: str,
        outcome: str,
    ) -> Notification:
        """Create notification for completed sequence."""
        return self.create_notification(
            type=NotificationType.SEQUENCE_COMPLETED,
            title=f"Sequence completed: {contact_name}",
            message=f"{sequence_name} for {contact_name} completed with outcome: {outcome}",
            priority=NotificationPriority.MEDIUM,
            data={
                "contact_name": contact_name,
                "sequence_name": sequence_name,
                "outcome": outcome,
            },
        )
    
    def create_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.URGENT,
    ) -> Notification:
        """Create an urgent alert."""
        return self.create_notification(
            type=NotificationType.ALERT,
            title=title,
            message=message,
            priority=priority,
        )
    
    async def generate_daily_summary(self) -> Notification:
        """Generate daily activity summary."""
        try:
            from src.dashboard import get_dashboard_aggregator
            aggregator = get_dashboard_aggregator()
            metrics = await aggregator.refresh_metrics()
            
            summary_parts = [
                f"📧 Drafts sent: {metrics.drafts_sent_today}",
                f"💬 Replies: {metrics.contacts_replied}",
                f"📅 Meetings: {metrics.meetings_scheduled}",
                f"🔄 Active sequences: {metrics.sequences_active}",
                f"📊 Reply rate: {metrics.reply_rate}%",
            ]
            
            message = "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            message = "Daily summary unavailable"
        
        return self.create_notification(
            type=NotificationType.DAILY_SUMMARY,
            title="Daily Activity Summary",
            message=message,
            priority=NotificationPriority.LOW,
            channel=NotificationChannel.EMAIL,
        )
    
    def get_unread(self) -> List[Dict[str, Any]]:
        """Get unread notifications."""
        return [
            n.to_dict() for n in self.notifications
            if n.read_at is None
        ]
    
    def get_all(
        self,
        type_filter: Optional[NotificationType] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get all notifications."""
        notifications = self.notifications
        
        if type_filter:
            notifications = [n for n in notifications if n.type == type_filter]
        
        return [
            n.to_dict() for n in 
            sorted(notifications, key=lambda x: x.created_at, reverse=True)[:limit]
        ]
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark notification as read."""
        for n in self.notifications:
            if n.id == notification_id:
                n.read_at = datetime.utcnow()
                return True
        return False
    
    def mark_all_read(self) -> int:
        """Mark all notifications as read."""
        count = 0
        for n in self.notifications:
            if n.read_at is None:
                n.read_at = datetime.utcnow()
                count += 1
        return count
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self.notifications if n.read_at is None)
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update notification settings."""
        self.notification_settings.update(settings)


# Singleton
_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get singleton notification service."""
    global _service
    if _service is None:
        _service = NotificationService()
    return _service
