"""
Notification Model for Jarvis Proactive Alerts.

This model stores notifications that Jarvis creates proactively
when it detects signals that need attention.

Priority levels:
- urgent: Needs immediate attention (email reply, hot lead)
- high: Important but not time-critical (deal update, overdue item)  
- normal: Informational (daily summary, stale items)
- low: Nice to know (analytics, suggestions)
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.db import Base, SafeJSON


class JarvisNotification(Base):
    """
    Proactive notification from Jarvis.
    
    Created when the daemon monitor detects signals that need
    user attention - Henry-style proactive behavior.
    """
    __tablename__ = "jarvis_notifications"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User targeting
    user_id = Column(String(255), nullable=False, index=True)
    
    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Priority: urgent, high, normal, low
    priority = Column(String(50), default="normal", index=True)
    
    # Action configuration
    action_type = Column(String(100), nullable=True)  # view_forms, view_deals, etc.
    action_url = Column(String(500), nullable=True)   # Where to navigate
    action_data = Column(SafeJSON, default=dict)         # Additional context
    
    # Status tracking
    is_read = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)  # User explicitly dismissed
    is_actioned = Column(Boolean, default=False)      # User took the action
    
    # Delivery tracking (for future: push, email, voice)
    delivered_via = Column(SafeJSON, default=list)  # ["in_app", "push", "email"]
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Auto-dismiss after this time
    
    # Indexes
    __table_args__ = (
        Index("ix_jarvis_notifications_user_unread", "user_id", "is_read"),
        Index("ix_jarvis_notifications_priority", "priority", "created_at"),
        Index("ix_jarvis_notifications_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<JarvisNotification(id={self.id}, title='{self.title[:30]}...', priority={self.priority})>"
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "action_type": self.action_type,
            "action_url": self.action_url,
            "action_data": self.action_data or {},
            "is_read": self.is_read,
            "is_acknowledged": self.is_acknowledged,
            "is_actioned": self.is_actioned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


# Priority weights for sorting
PRIORITY_WEIGHTS = {
    "urgent": 100,
    "high": 75,
    "normal": 50,
    "low": 25,
}


def get_priority_weight(priority: str) -> int:
    """Get numeric weight for priority sorting."""
    return PRIORITY_WEIGHTS.get(priority, 50)
