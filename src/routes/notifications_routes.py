"""
Notifications Routes - Alert and notification management
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationType(str, Enum):
    DEAL_UPDATE = "deal_update"
    TASK_DUE = "task_due"
    MENTION = "mention"
    ASSIGNMENT = "assignment"
    MILESTONE = "milestone"
    ALERT = "alert"
    SYSTEM = "system"
    REMINDER = "reminder"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PUSH = "push"
    TEAMS = "teams"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# In-memory storage
notifications = {}
notification_preferences = {}
notification_templates = {}
notification_rules = {}


class NotificationCreate(BaseModel):
    type: NotificationType
    title: str
    message: str
    recipient_id: str
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    priority: NotificationPriority = NotificationPriority.MEDIUM
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action_url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class PreferencesUpdate(BaseModel):
    channel_preferences: Dict[str, bool]
    type_preferences: Dict[str, bool]
    quiet_hours: Optional[Dict[str, str]] = None
    digest_frequency: Optional[str] = None


class NotificationRuleCreate(BaseModel):
    name: str
    trigger_type: str  # event type that triggers
    conditions: Dict[str, Any] = {}
    notification_type: NotificationType
    channels: List[NotificationChannel]
    template_id: Optional[str] = None
    is_active: bool = True


# Core CRUD
@router.post("")
async def create_notification(
    request: NotificationCreate,
    tenant_id: str = Query(default="default")
):
    """Create and send a notification"""
    notification_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    notification = {
        "id": notification_id,
        "type": request.type.value,
        "title": request.title,
        "message": request.message,
        "recipient_id": request.recipient_id,
        "channels": [c.value for c in request.channels],
        "priority": request.priority.value,
        "entity_type": request.entity_type,
        "entity_id": request.entity_id,
        "action_url": request.action_url,
        "data": request.data or {},
        "is_read": False,
        "read_at": None,
        "is_archived": False,
        "delivered_via": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Simulate delivery
    notification["delivered_via"] = [c.value for c in request.channels]
    notification["delivered_at"] = now.isoformat()
    
    notifications[notification_id] = notification
    
    logger.info("notification_created", notification_id=notification_id)
    
    return notification


@router.get("")
async def list_notifications(
    recipient_id: Optional[str] = None,
    type: Optional[NotificationType] = None,
    is_read: Optional[bool] = None,
    priority: Optional[NotificationPriority] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List notifications with filters"""
    result = [n for n in notifications.values() if n.get("tenant_id") == tenant_id]
    
    if recipient_id:
        result = [n for n in result if n.get("recipient_id") == recipient_id]
    if type:
        result = [n for n in result if n.get("type") == type.value]
    if is_read is not None:
        result = [n for n in result if n.get("is_read") == is_read]
    if priority:
        result = [n for n in result if n.get("priority") == priority.value]
    
    # Sort by created_at descending
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "notifications": result[offset:offset + limit],
        "total": len(result),
        "unread_count": sum(1 for n in result if not n.get("is_read"))
    }


@router.get("/{notification_id}")
async def get_notification(
    notification_id: str,
    tenant_id: str = Query(default="default")
):
    """Get notification details"""
    if notification_id not in notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notifications[notification_id]


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    tenant_id: str = Query(default="default")
):
    """Mark notification as read"""
    if notification_id not in notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notifications[notification_id]["is_read"] = True
    notifications[notification_id]["read_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "notification_id": notification_id}


@router.post("/mark-all-read")
async def mark_all_as_read(
    recipient_id: str = Query(...),
    tenant_id: str = Query(default="default")
):
    """Mark all notifications as read for a user"""
    count = 0
    now = datetime.utcnow().isoformat()
    
    for notification in notifications.values():
        if (notification.get("recipient_id") == recipient_id and 
            notification.get("tenant_id") == tenant_id and
            not notification.get("is_read")):
            notification["is_read"] = True
            notification["read_at"] = now
            count += 1
    
    return {"success": True, "marked_read": count}


@router.patch("/{notification_id}/archive")
async def archive_notification(
    notification_id: str,
    tenant_id: str = Query(default="default")
):
    """Archive a notification"""
    if notification_id not in notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notifications[notification_id]["is_archived"] = True
    notifications[notification_id]["archived_at"] = datetime.utcnow().isoformat()
    
    return {"success": True, "notification_id": notification_id}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    tenant_id: str = Query(default="default")
):
    """Delete a notification"""
    if notification_id not in notifications:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    del notifications[notification_id]
    
    return {"success": True, "deleted": notification_id}


# Preferences
@router.get("/users/{user_id}/preferences")
async def get_user_preferences(
    user_id: str,
    tenant_id: str = Query(default="default")
):
    """Get notification preferences for a user"""
    key = f"{tenant_id}:{user_id}"
    
    if key not in notification_preferences:
        return {
            "user_id": user_id,
            "channel_preferences": {
                "in_app": True,
                "email": True,
                "sms": False,
                "slack": True,
                "push": True
            },
            "type_preferences": {
                "deal_update": True,
                "task_due": True,
                "mention": True,
                "assignment": True,
                "milestone": True,
                "alert": True,
                "system": True
            },
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00",
                "timezone": "UTC"
            },
            "digest_frequency": "daily"
        }
    
    return notification_preferences[key]


@router.put("/users/{user_id}/preferences")
async def update_user_preferences(
    user_id: str,
    request: PreferencesUpdate,
    tenant_id: str = Query(default="default")
):
    """Update notification preferences for a user"""
    key = f"{tenant_id}:{user_id}"
    
    notification_preferences[key] = {
        "user_id": user_id,
        "channel_preferences": request.channel_preferences,
        "type_preferences": request.type_preferences,
        "quiet_hours": request.quiet_hours,
        "digest_frequency": request.digest_frequency,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return notification_preferences[key]


# Notification Rules
@router.post("/rules")
async def create_notification_rule(
    request: NotificationRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a notification rule"""
    rule_id = str(uuid.uuid4())
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "trigger_type": request.trigger_type,
        "conditions": request.conditions,
        "notification_type": request.notification_type.value,
        "channels": [c.value for c in request.channels],
        "template_id": request.template_id,
        "is_active": request.is_active,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    notification_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_notification_rules(tenant_id: str = Query(default="default")):
    """List notification rules"""
    result = [r for r in notification_rules.values() if r.get("tenant_id") == tenant_id]
    return {"rules": result, "total": len(result)}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: str,
    tenant_id: str = Query(default="default")
):
    """Toggle a notification rule on/off"""
    if rule_id not in notification_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    notification_rules[rule_id]["is_active"] = not notification_rules[rule_id]["is_active"]
    
    return notification_rules[rule_id]


# Bulk Operations
@router.post("/bulk")
async def send_bulk_notification(
    notification: NotificationCreate,
    recipient_ids: List[str] = Query(...),
    tenant_id: str = Query(default="default")
):
    """Send notification to multiple recipients"""
    sent = []
    
    for recipient_id in recipient_ids:
        notification_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        notif = {
            "id": notification_id,
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "recipient_id": recipient_id,
            "channels": [c.value for c in notification.channels],
            "priority": notification.priority.value,
            "entity_type": notification.entity_type,
            "entity_id": notification.entity_id,
            "action_url": notification.action_url,
            "data": notification.data or {},
            "is_read": False,
            "is_archived": False,
            "tenant_id": tenant_id,
            "created_at": now.isoformat()
        }
        
        notifications[notification_id] = notif
        sent.append(notification_id)
    
    return {"success": True, "sent_count": len(sent), "notification_ids": sent}


# Stats
@router.get("/stats")
async def get_notification_stats(
    days: int = Query(default=7, ge=1, le=30),
    tenant_id: str = Query(default="default")
):
    """Get notification statistics"""
    return {
        "period_days": days,
        "total_sent": random.randint(1000, 10000),
        "total_read": random.randint(700, 8000),
        "read_rate": round(random.uniform(0.65, 0.90), 3),
        "by_type": {
            "deal_update": random.randint(100, 1000),
            "task_due": random.randint(200, 1500),
            "mention": random.randint(50, 500),
            "assignment": random.randint(100, 800),
            "alert": random.randint(50, 300)
        },
        "by_channel": {
            "in_app": random.randint(500, 5000),
            "email": random.randint(300, 3000),
            "slack": random.randint(100, 1000),
            "push": random.randint(200, 2000)
        },
        "avg_time_to_read_seconds": random.randint(60, 600)
    }


# Feed/Timeline
@router.get("/feed/{user_id}")
async def get_notification_feed(
    user_id: str,
    limit: int = Query(default=20, le=50),
    before: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get paginated notification feed for a user"""
    user_notifications = [
        n for n in notifications.values()
        if n.get("recipient_id") == user_id and n.get("tenant_id") == tenant_id
    ]
    
    user_notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    if before:
        user_notifications = [
            n for n in user_notifications
            if n.get("created_at", "") < before
        ]
    
    return {
        "notifications": user_notifications[:limit],
        "has_more": len(user_notifications) > limit,
        "unread_count": sum(1 for n in user_notifications if not n.get("is_read"))
    }
