"""
Notification Routes.

API endpoints for notifications and alerts.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.notifications import (
    get_notification_service,
    NotificationType,
    NotificationPriority,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class CreateAlertRequest(BaseModel):
    title: str
    message: str
    priority: str = "medium"


class UpdateSettingsRequest(BaseModel):
    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    slack_webhook: Optional[str] = None
    daily_summary_time: Optional[str] = None


@router.get("/")
async def get_notifications(
    type: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get all notifications."""
    service = get_notification_service()
    
    type_filter = None
    if type:
        try:
            type_filter = NotificationType(type)
        except ValueError:
            pass
    
    notifications = service.get_all(type_filter=type_filter, limit=limit)
    
    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": service.get_unread_count(),
    }


@router.get("/unread")
async def get_unread() -> Dict[str, Any]:
    """Get unread notifications."""
    service = get_notification_service()
    notifications = service.get_unread()
    
    return {
        "notifications": notifications,
        "count": len(notifications),
    }


@router.get("/count")
async def get_count() -> Dict[str, Any]:
    """Get notification counts."""
    service = get_notification_service()
    
    return {
        "unread": service.get_unread_count(),
        "total": len(service.notifications),
    }


@router.post("/alert")
async def create_alert(request: CreateAlertRequest) -> Dict[str, Any]:
    """Create a custom alert."""
    service = get_notification_service()
    
    try:
        priority = NotificationPriority(request.priority)
    except ValueError:
        priority = NotificationPriority.MEDIUM
    
    notification = service.create_alert(
        title=request.title,
        message=request.message,
        priority=priority,
    )
    
    return {
        "status": "success",
        "notification": notification.to_dict(),
    }


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str) -> Dict[str, Any]:
    """Mark notification as read."""
    service = get_notification_service()
    
    success = service.mark_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "status": "success",
    }


@router.post("/mark-all-read")
async def mark_all_read() -> Dict[str, Any]:
    """Mark all notifications as read."""
    service = get_notification_service()
    count = service.mark_all_read()
    
    return {
        "status": "success",
        "marked_count": count,
    }


@router.post("/daily-summary")
async def generate_daily_summary() -> Dict[str, Any]:
    """Generate and send daily summary."""
    service = get_notification_service()
    notification = await service.generate_daily_summary()
    
    return {
        "status": "success",
        "notification": notification.to_dict(),
    }


@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Get notification settings."""
    service = get_notification_service()
    
    return {
        "settings": service.notification_settings,
    }


@router.post("/settings")
async def update_settings(request: UpdateSettingsRequest) -> Dict[str, Any]:
    """Update notification settings."""
    service = get_notification_service()
    
    updates = {}
    if request.email_enabled is not None:
        updates["email_enabled"] = request.email_enabled
    if request.slack_enabled is not None:
        updates["slack_enabled"] = request.slack_enabled
    if request.slack_webhook is not None:
        updates["slack_webhook"] = request.slack_webhook
    if request.daily_summary_time is not None:
        updates["daily_summary_time"] = request.daily_summary_time
    
    service.update_settings(updates)
    
    return {
        "status": "success",
        "settings": service.notification_settings,
    }
