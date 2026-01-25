"""
Notification Service for Jarvis Proactive Alerts.

This service manages the notification lifecycle:
- Create notifications from daemon monitor
- Retrieve unread notifications
- Mark as read/acknowledged
- Cleanup expired notifications
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy import select, and_, or_, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.notification import JarvisNotification, PRIORITY_WEIGHTS
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


class NotificationService:
    """
    Service for managing Jarvis notifications.
    
    Provides CRUD operations and smart retrieval for
    the "Hey Jarvis, what's up?" pattern.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
    
    # =========================================================================
    # Create Notifications
    # =========================================================================
    
    async def create(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        action_type: Optional[str] = None,
        action_url: Optional[str] = None,
        action_data: Optional[Dict] = None,
        expires_in_hours: Optional[int] = None,
    ) -> JarvisNotification:
        """
        Create a new notification.
        
        Args:
            user_id: Target user
            title: Notification title
            message: Notification body
            priority: urgent, high, normal, low
            action_type: Type of action (view_forms, view_deals, etc.)
            action_url: URL to navigate to
            action_data: Additional context
            expires_in_hours: Auto-expire after this many hours
            
        Returns:
            Created notification
        """
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        notification = JarvisNotification(
            user_id=user_id,
            title=title,
            message=message,
            priority=priority,
            action_type=action_type,
            action_url=action_url,
            action_data=action_data or {},
            expires_at=expires_at,
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        log_event(
            "notification_created",
            notification_id=str(notification.id),
            user_id=user_id,
            priority=priority,
        )
        
        return notification
    
    # =========================================================================
    # Retrieve Notifications
    # =========================================================================
    
    async def get_unread(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[JarvisNotification]:
        """
        Get unread notifications for a user.
        
        Sorted by priority weight + recency.
        """
        result = await self.db.execute(
            select(JarvisNotification)
            .where(
                and_(
                    JarvisNotification.user_id == user_id,
                    JarvisNotification.is_read == False,
                    or_(
                        JarvisNotification.expires_at.is_(None),
                        JarvisNotification.expires_at > datetime.utcnow()
                    )
                )
            )
            .order_by(
                # Custom priority ordering
                desc(
                    func.case(
                        (JarvisNotification.priority == "urgent", 100),
                        (JarvisNotification.priority == "high", 75),
                        (JarvisNotification.priority == "normal", 50),
                        else_=25
                    )
                ),
                desc(JarvisNotification.created_at)
            )
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def get_whats_up(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get the "Hey Jarvis, what's up?" summary.
        
        Returns:
            Summary with urgent items, counts by priority, and suggestions
        """
        # Get all unread
        unread = await self.get_unread(user_id, limit=50)
        
        # Count by priority
        by_priority = {"urgent": 0, "high": 0, "normal": 0, "low": 0}
        for n in unread:
            by_priority[n.priority] = by_priority.get(n.priority, 0) + 1
        
        # Get top items (urgent + high)
        top_items = [n for n in unread if n.priority in ("urgent", "high")][:5]
        
        # Generate summary message
        total = len(unread)
        if total == 0:
            summary = "All clear! No pending notifications."
        elif by_priority["urgent"] > 0:
            summary = f"🚨 {by_priority['urgent']} urgent item(s) need your attention!"
        elif by_priority["high"] > 0:
            summary = f"📋 {by_priority['high']} high-priority item(s) waiting for you."
        else:
            summary = f"📬 {total} notification(s) to review when you have a moment."
        
        return {
            "summary": summary,
            "total_unread": total,
            "by_priority": by_priority,
            "top_items": [n.to_dict() for n in top_items],
            "has_urgent": by_priority["urgent"] > 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def get_recent(
        self,
        user_id: str,
        limit: int = 20,
        include_read: bool = False,
    ) -> List[JarvisNotification]:
        """Get recent notifications."""
        query = select(JarvisNotification).where(
            JarvisNotification.user_id == user_id
        )
        
        if not include_read:
            query = query.where(JarvisNotification.is_read == False)
        
        result = await self.db.execute(
            query.order_by(desc(JarvisNotification.created_at)).limit(limit)
        )
        
        return list(result.scalars().all())
    
    # =========================================================================
    # Update Notifications
    # =========================================================================
    
    async def mark_read(
        self,
        notification_id: str,
    ) -> bool:
        """Mark a notification as read."""
        result = await self.db.execute(
            update(JarvisNotification)
            .where(JarvisNotification.id == uuid.UUID(notification_id))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def mark_acknowledged(
        self,
        notification_id: str,
    ) -> bool:
        """Mark a notification as acknowledged (dismissed)."""
        result = await self.db.execute(
            update(JarvisNotification)
            .where(JarvisNotification.id == uuid.UUID(notification_id))
            .values(
                is_acknowledged=True,
                acknowledged_at=datetime.utcnow(),
                is_read=True,
                read_at=datetime.utcnow(),
            )
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def mark_actioned(
        self,
        notification_id: str,
    ) -> bool:
        """Mark that the user took the suggested action."""
        result = await self.db.execute(
            update(JarvisNotification)
            .where(JarvisNotification.id == uuid.UUID(notification_id))
            .values(
                is_actioned=True,
                is_acknowledged=True,
                is_read=True,
            )
        )
        await self.db.commit()
        
        log_event("notification_actioned", notification_id=notification_id)
        
        return result.rowcount > 0
    
    async def mark_all_read(
        self,
        user_id: str,
    ) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            update(JarvisNotification)
            .where(
                and_(
                    JarvisNotification.user_id == user_id,
                    JarvisNotification.is_read == False
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.commit()
        
        return result.rowcount
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def cleanup_expired(self) -> int:
        """Remove expired notifications."""
        from sqlalchemy import delete
        
        result = await self.db.execute(
            delete(JarvisNotification).where(
                and_(
                    JarvisNotification.expires_at.isnot(None),
                    JarvisNotification.expires_at < datetime.utcnow()
                )
            )
        )
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"🧹 Cleaned up {result.rowcount} expired notifications")
        
        return result.rowcount
    
    async def cleanup_old_read(
        self,
        days: int = 30,
    ) -> int:
        """Remove old read notifications."""
        from sqlalchemy import delete
        
        threshold = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            delete(JarvisNotification).where(
                and_(
                    JarvisNotification.is_read == True,
                    JarvisNotification.created_at < threshold
                )
            )
        )
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"🧹 Cleaned up {result.rowcount} old read notifications")
        
        return result.rowcount
