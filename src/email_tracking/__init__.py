"""
Email Tracking Module - Email Engagement Tracking
=================================================
Handles email opens, clicks, and engagement analytics.
"""

from .email_tracking_service import (
    EmailTrackingService,
    EmailTrack,
    EmailOpen,
    EmailClick,
    EmailReply,
    get_email_tracking_service,
    EmailStatus,
    BounceType,
)

__all__ = [
    "EmailTrackingService",
    "EmailTrack",
    "EmailOpen",
    "EmailClick",
    "EmailReply",
    "get_email_tracking_service",
    "EmailStatus",
    "BounceType",
]
