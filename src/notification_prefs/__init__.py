"""
Notification Preferences Module
================================
User notification preferences and settings.
"""

from .notification_prefs_service import (
    NotificationPrefsService,
    NotificationPreference,
    NotificationChannel,
    NotificationType,
    get_notification_prefs_service,
)

__all__ = [
    "NotificationPrefsService",
    "NotificationPreference",
    "NotificationChannel",
    "NotificationType",
    "get_notification_prefs_service",
]
