"""
Reply Detection Webhook Routes.

Handles webhooks for detecting email replies.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Request

from src.tracking import get_reply_detector
from src.analytics import get_analytics_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gmail-push")
async def gmail_push_notification(request: Request) -> Dict[str, Any]:
    """Handle Gmail push notifications for new emails.
    
    This would be configured with Gmail Push Notifications API.
    """
    try:
        body = await request.json()
        
        # Gmail push notifications come as Pub/Sub messages
        message = body.get("message", {})
        data = message.get("data", "")
        
        logger.info(f"Received Gmail push notification: {message.get('messageId')}")
        
        # Trigger reply check
        detector = get_reply_detector()
        replies = await detector.check_for_replies(since_hours=1)
        
        # Track replies in analytics
        analytics = get_analytics_engine()
        for reply in replies:
            analytics.track_event(
                event_type="replied",
                contact_email=reply.get("from", ""),
                metadata={"subject": reply.get("subject")},
            )
        
        return {
            "status": "success",
            "replies_detected": len(replies),
        }
        
    except Exception as e:
        logger.error(f"Error processing Gmail push: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/hubspot-engagement")
async def hubspot_engagement_webhook(request: Request) -> Dict[str, Any]:
    """Handle HubSpot engagement webhooks (opens, clicks, etc.).
    
    Configure in HubSpot: Settings > Integrations > Webhooks
    """
    try:
        body = await request.json()
        
        # HubSpot sends array of events
        events = body if isinstance(body, list) else [body]
        
        analytics = get_analytics_engine()
        processed = 0
        
        for event in events:
            event_type = event.get("eventType", "")
            
            # Map HubSpot event types to our types
            type_map = {
                "email.open": "opened",
                "email.click": "clicked",
                "email.bounce": "bounced",
                "email.delivered": "sent",
            }
            
            our_type = type_map.get(event_type)
            if our_type:
                recipient = event.get("recipient") or event.get("properties", {}).get("hs_email_recipient")
                
                if recipient:
                    analytics.track_event(
                        event_type=our_type,
                        contact_email=recipient,
                        campaign_id=event.get("campaignId"),
                        metadata={"hubspot_event": event_type},
                    )
                    processed += 1
        
        logger.info(f"Processed {processed} HubSpot engagement events")
        
        return {
            "status": "success",
            "processed": processed,
        }
        
    except Exception as e:
        logger.error(f"Error processing HubSpot webhook: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/check-replies")
async def manual_check_replies(hours: int = 24) -> Dict[str, Any]:
    """Manually trigger a reply check.
    
    Args:
        hours: Look back this many hours
    """
    detector = get_reply_detector()
    replies = await detector.check_for_replies(since_hours=hours)
    
    # Track in analytics
    analytics = get_analytics_engine()
    for reply in replies:
        analytics.track_event(
            event_type="replied",
            contact_email=reply.get("from", ""),
            metadata={"subject": reply.get("subject")},
        )
    
    return {
        "status": "success",
        "replies_found": len(replies),
        "replies": replies,
    }
