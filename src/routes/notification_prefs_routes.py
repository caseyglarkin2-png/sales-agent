"""
Notification Preferences Routes - User Notification Settings API
=================================================================
REST API endpoints for managing user notification preferences.
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Optional
from pydantic import BaseModel

from ..notification_prefs import (
    NotificationPrefsService,
    NotificationChannel,
    NotificationType,
    get_notification_prefs_service,
)
from ..notification_prefs.notification_prefs_service import Frequency


router = APIRouter(prefix="/notification-preferences", tags=["Notification Preferences"])


# Request models
class UpdateGlobalSettingsRequest(BaseModel):
    """Update global settings request."""
    global_enabled: Optional[bool] = None
    quiet_hours: Optional[dict[str, Any]] = None
    digest: Optional[dict[str, Any]] = None


class UpdateChannelRequest(BaseModel):
    """Update channel request."""
    enabled: Optional[bool] = None
    address: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class VerifyChannelRequest(BaseModel):
    """Verify channel request."""
    verification_code: str


class UpdatePreferenceRequest(BaseModel):
    """Update preference request."""
    enabled: Optional[bool] = None
    channels: Optional[dict[str, bool]] = None
    frequency: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None


class BulkUpdatePreferencesRequest(BaseModel):
    """Bulk update preferences request."""
    updates: list[dict[str, Any]]


class ShouldNotifyRequest(BaseModel):
    """Should notify check request."""
    notification_type: str
    channel: str
    context: Optional[dict[str, Any]] = None


def get_service() -> NotificationPrefsService:
    """Get notification preferences service instance."""
    return get_notification_prefs_service()


# Enums
@router.get("/notification-types")
async def list_notification_types():
    """List available notification types."""
    return {
        "notification_types": [
            {"value": t.value, "name": t.name}
            for t in NotificationType
        ]
    }


@router.get("/channels")
async def list_channels():
    """List available notification channels."""
    return {
        "channels": [
            {"value": c.value, "name": c.name}
            for c in NotificationChannel
        ]
    }


@router.get("/frequencies")
async def list_frequencies():
    """List available notification frequencies."""
    return {
        "frequencies": [
            {"value": f.value, "name": f.name}
            for f in Frequency
        ]
    }


# User settings
@router.get("/users/{user_id}")
async def get_user_settings(user_id: str):
    """Get notification settings for a user."""
    service = get_service()
    settings = await service.get_user_settings(user_id)
    
    return {
        "user_id": settings.user_id,
        "global_enabled": settings.global_enabled,
        "channels": [
            {
                "channel": cs.channel.value,
                "enabled": cs.enabled,
                "address": cs.address,
                "verified": cs.verified,
            }
            for cs in settings.channels
        ],
        "quiet_hours": {
            "enabled": settings.quiet_hours.enabled,
            "start_time": settings.quiet_hours.start_time.strftime("%H:%M") if settings.quiet_hours.start_time else None,
            "end_time": settings.quiet_hours.end_time.strftime("%H:%M") if settings.quiet_hours.end_time else None,
            "timezone": settings.quiet_hours.timezone,
            "days": settings.quiet_hours.days,
        },
        "digest": {
            "enabled": settings.digest.enabled,
            "frequency": settings.digest.frequency.value,
            "send_time": settings.digest.send_time.strftime("%H:%M") if settings.digest.send_time else None,
            "timezone": settings.digest.timezone,
        },
        "preferences_count": len(settings.preferences),
        "updated_at": settings.updated_at.isoformat(),
    }


@router.patch("/users/{user_id}")
async def update_global_settings(user_id: str, request: UpdateGlobalSettingsRequest):
    """Update global notification settings."""
    service = get_service()
    
    settings = await service.update_global_settings(
        user_id=user_id,
        global_enabled=request.global_enabled,
        quiet_hours=request.quiet_hours,
        digest=request.digest,
    )
    
    return {"success": True, "user_id": user_id}


@router.post("/users/{user_id}/reset")
async def reset_to_defaults(user_id: str):
    """Reset user settings to defaults."""
    service = get_service()
    settings = await service.reset_to_defaults(user_id)
    
    return {"success": True, "user_id": user_id}


# Channel management
@router.get("/users/{user_id}/channels")
async def get_user_channels(user_id: str):
    """Get user's notification channels."""
    service = get_service()
    settings = await service.get_user_settings(user_id)
    
    return {
        "channels": [
            {
                "channel": cs.channel.value,
                "enabled": cs.enabled,
                "address": cs.address,
                "verified": cs.verified,
                "verified_at": cs.verified_at.isoformat() if cs.verified_at else None,
            }
            for cs in settings.channels
        ]
    }


@router.patch("/users/{user_id}/channels/{channel}")
async def update_channel(user_id: str, channel: str, request: UpdateChannelRequest):
    """Update a notification channel."""
    service = get_service()
    
    try:
        ch = NotificationChannel(channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    channel_settings = await service.update_channel(
        user_id=user_id,
        channel=ch,
        enabled=request.enabled,
        address=request.address,
        channel_settings=request.settings,
    )
    
    return {
        "channel": channel_settings.channel.value,
        "enabled": channel_settings.enabled,
        "verified": channel_settings.verified,
    }


@router.post("/users/{user_id}/channels/{channel}/verify")
async def verify_channel(user_id: str, channel: str, request: VerifyChannelRequest):
    """Verify a notification channel."""
    service = get_service()
    
    try:
        ch = NotificationChannel(channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    if not await service.verify_channel(user_id, ch, request.verification_code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    return {"success": True, "verified": True}


# Preferences
@router.get("/users/{user_id}/preferences")
async def get_user_preferences(user_id: str):
    """Get all notification preferences for a user."""
    service = get_service()
    settings = await service.get_user_settings(user_id)
    
    return {
        "preferences": [
            {
                "id": pref.id,
                "notification_type": pref.notification_type.value,
                "enabled": pref.enabled,
                "channels": {ch.value: en for ch, en in pref.channels.items()},
                "frequency": pref.frequency.value,
                "conditions": pref.conditions,
            }
            for pref in settings.preferences.values()
        ]
    }


@router.get("/users/{user_id}/preferences/{notification_type}")
async def get_preference(user_id: str, notification_type: str):
    """Get preference for a specific notification type."""
    service = get_service()
    
    try:
        ntype = NotificationType(notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    pref = await service.get_preference(user_id, ntype)
    
    if not pref:
        return {"notification_type": notification_type, "preference": None}
    
    return {
        "id": pref.id,
        "notification_type": pref.notification_type.value,
        "enabled": pref.enabled,
        "channels": {ch.value: en for ch, en in pref.channels.items()},
        "frequency": pref.frequency.value,
        "conditions": pref.conditions,
        "updated_at": pref.updated_at.isoformat(),
    }


@router.patch("/users/{user_id}/preferences/{notification_type}")
async def update_preference(user_id: str, notification_type: str, request: UpdatePreferenceRequest):
    """Update preference for a notification type."""
    service = get_service()
    
    try:
        ntype = NotificationType(notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    frequency = None
    if request.frequency:
        try:
            frequency = Frequency(request.frequency)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid frequency")
    
    pref = await service.update_preference(
        user_id=user_id,
        notification_type=ntype,
        enabled=request.enabled,
        channels=request.channels,
        frequency=frequency,
        conditions=request.conditions,
    )
    
    return {
        "id": pref.id,
        "notification_type": pref.notification_type.value,
        "enabled": pref.enabled,
    }


@router.post("/users/{user_id}/preferences/bulk")
async def bulk_update_preferences(user_id: str, request: BulkUpdatePreferencesRequest):
    """Bulk update multiple preferences."""
    service = get_service()
    
    updated = await service.bulk_update_preferences(user_id, request.updates)
    
    return {
        "success": True,
        "updated_count": updated,
    }


# Notification delivery
@router.post("/users/{user_id}/should-notify")
async def should_notify(user_id: str, request: ShouldNotifyRequest):
    """Check if a user should receive a notification."""
    service = get_service()
    
    try:
        ntype = NotificationType(request.notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    try:
        channel = NotificationChannel(request.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    should = await service.should_notify(
        user_id=user_id,
        notification_type=ntype,
        channel=channel,
        context=request.context,
    )
    
    return {
        "user_id": user_id,
        "notification_type": request.notification_type,
        "channel": request.channel,
        "should_notify": should,
    }


@router.get("/users/{user_id}/delivery-channels/{notification_type}")
async def get_delivery_channels(user_id: str, notification_type: str):
    """Get enabled channels for a notification type."""
    service = get_service()
    
    try:
        ntype = NotificationType(notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    channels = await service.get_delivery_channels(user_id, ntype)
    
    return {
        "user_id": user_id,
        "notification_type": notification_type,
        "channels": [c.value for c in channels],
    }
