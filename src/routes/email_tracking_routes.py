"""
Email Tracking Routes - Email Engagement Tracking API
=====================================================
REST API endpoints for email tracking and analytics.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..email_tracking import (
    EmailTrackingService,
    EmailStatus,
    BounceType,
    get_email_tracking_service,
)


router = APIRouter(prefix="/email-tracking", tags=["Email Tracking"])


# Request/Response models
class CreateTrackingRequest(BaseModel):
    """Create tracking request."""
    message_id: str
    subject: str
    recipient_email: str
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    sequence_id: Optional[str] = None
    campaign_id: Optional[str] = None
    user_id: Optional[str] = None
    tracked_links: Optional[list[dict[str, str]]] = None


class RecordOpenRequest(BaseModel):
    """Record open request."""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class RecordClickRequest(BaseModel):
    """Record click request."""
    url: str
    link_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class RecordReplyRequest(BaseModel):
    """Record reply request."""
    subject: Optional[str] = None
    snippet: Optional[str] = None
    is_auto_reply: bool = False
    sentiment: Optional[str] = None
    message_id: Optional[str] = None


class RecordBounceRequest(BaseModel):
    """Record bounce request."""
    bounce_type: str = "soft"
    reason: Optional[str] = None
    diagnostic_code: Optional[str] = None


def get_service() -> EmailTrackingService:
    """Get email tracking service instance."""
    return get_email_tracking_service()


# Tracking CRUD
@router.post("")
async def create_tracking(request: CreateTrackingRequest):
    """Create email tracking record."""
    service = get_service()
    
    email = await service.create_tracking(
        message_id=request.message_id,
        subject=request.subject,
        recipient_email=request.recipient_email,
        contact_id=request.contact_id,
        account_id=request.account_id,
        sequence_id=request.sequence_id,
        campaign_id=request.campaign_id,
        user_id=request.user_id,
        tracked_links=request.tracked_links,
    )
    
    return {
        "id": email.id,
        "message_id": email.message_id,
        "open_tracking_id": email.open_tracking_id,
        "click_tracking_id": email.click_tracking_id,
        "status": email.status.value,
    }


@router.get("")
async def list_tracking(
    contact_id: Optional[str] = None,
    account_id: Optional[str] = None,
    sequence_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    """List email tracking records."""
    service = get_service()
    
    status_enum = None
    if status:
        try:
            status_enum = EmailStatus(status)
        except ValueError:
            pass
    
    emails, total = await service.list_tracking(
        contact_id=contact_id,
        account_id=account_id,
        sequence_id=sequence_id,
        campaign_id=campaign_id,
        user_id=user_id,
        status=status_enum,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "emails": [
            {
                "id": e.id,
                "message_id": e.message_id,
                "subject": e.subject,
                "recipient_email": e.recipient_email,
                "contact_id": e.contact_id,
                "status": e.status.value,
                "open_count": e.open_count,
                "click_count": e.click_count,
                "first_opened_at": e.first_opened_at.isoformat() if e.first_opened_at else None,
                "replied_at": e.replied_at.isoformat() if e.replied_at else None,
                "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            }
            for e in emails
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
async def get_email_stats(
    user_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    sequence_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
):
    """Get email statistics."""
    service = get_service()
    return await service.get_email_stats(
        user_id=user_id,
        campaign_id=campaign_id,
        sequence_id=sequence_id,
        from_date=from_date,
        to_date=to_date
    )


@router.get("/daily")
async def get_daily_stats(
    days: int = Query(default=30, le=90),
    user_id: Optional[str] = None
):
    """Get daily email statistics."""
    service = get_service()
    daily = await service.get_daily_stats(days=days, user_id=user_id)
    return {"daily": daily, "days": days}


@router.get("/links")
async def get_link_performance(
    campaign_id: Optional[str] = None,
    sequence_id: Optional[str] = None
):
    """Get link click performance."""
    service = get_service()
    links = await service.get_link_performance(
        campaign_id=campaign_id,
        sequence_id=sequence_id
    )
    return {"links": links}


@router.get("/devices")
async def get_device_breakdown(campaign_id: Optional[str] = None):
    """Get device type breakdown."""
    service = get_service()
    devices = await service.get_device_breakdown(campaign_id=campaign_id)
    return {"devices": devices}


@router.get("/{email_id}")
async def get_tracking(email_id: str):
    """Get email tracking by ID."""
    service = get_service()
    email = await service.get_tracking(email_id)
    
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "id": email.id,
        "message_id": email.message_id,
        "subject": email.subject,
        "recipient_email": email.recipient_email,
        "contact_id": email.contact_id,
        "account_id": email.account_id,
        "sequence_id": email.sequence_id,
        "campaign_id": email.campaign_id,
        "user_id": email.user_id,
        "status": email.status.value,
        "open_count": email.open_count,
        "click_count": email.click_count,
        "unique_clicks": email.unique_clicks,
        "opens": [
            {
                "id": o.id,
                "opened_at": o.opened_at.isoformat(),
                "device_type": o.device_type,
                "country": o.country,
            }
            for o in email.opens
        ],
        "clicks": [
            {
                "id": c.id,
                "url": c.url,
                "clicked_at": c.clicked_at.isoformat(),
                "device_type": c.device_type,
            }
            for c in email.clicks
        ],
        "replies": [
            {
                "id": r.id,
                "replied_at": r.replied_at.isoformat(),
                "is_auto_reply": r.is_auto_reply,
                "sentiment": r.sentiment,
            }
            for r in email.replies
        ],
        "bounce": {
            "type": email.bounce.bounce_type.value,
            "reason": email.bounce.reason,
            "bounced_at": email.bounce.bounced_at.isoformat(),
        } if email.bounce else None,
        "sent_at": email.sent_at.isoformat() if email.sent_at else None,
        "delivered_at": email.delivered_at.isoformat() if email.delivered_at else None,
        "first_opened_at": email.first_opened_at.isoformat() if email.first_opened_at else None,
        "last_opened_at": email.last_opened_at.isoformat() if email.last_opened_at else None,
        "first_clicked_at": email.first_clicked_at.isoformat() if email.first_clicked_at else None,
        "replied_at": email.replied_at.isoformat() if email.replied_at else None,
        "created_at": email.created_at.isoformat(),
    }


# Status updates
@router.post("/{email_id}/sent")
async def mark_sent(email_id: str):
    """Mark email as sent."""
    service = get_service()
    
    email = await service.mark_sent(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {"success": True, "status": email.status.value}


@router.post("/{email_id}/delivered")
async def mark_delivered(email_id: str):
    """Mark email as delivered."""
    service = get_service()
    
    email = await service.mark_delivered(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {"success": True, "status": email.status.value}


# Event recording
@router.post("/{email_id}/open")
async def record_open(email_id: str, request: RecordOpenRequest):
    """Record an email open."""
    service = get_service()
    
    open_event = await service.record_open_by_email_id(
        email_id,
        ip_address=request.ip_address,
        user_agent=request.user_agent
    )
    
    if not open_event:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "id": open_event.id,
        "opened_at": open_event.opened_at.isoformat(),
    }


@router.post("/{email_id}/click")
async def record_click(email_id: str, request: RecordClickRequest):
    """Record an email click."""
    service = get_service()
    
    email = await service.get_tracking(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    click = await service.record_click(
        email.click_tracking_id,
        url=request.url,
        link_id=request.link_id,
        ip_address=request.ip_address,
        user_agent=request.user_agent
    )
    
    if not click:
        raise HTTPException(status_code=400, detail="Failed to record click")
    
    return {
        "id": click.id,
        "clicked_at": click.clicked_at.isoformat(),
    }


@router.post("/{email_id}/reply")
async def record_reply(email_id: str, request: RecordReplyRequest):
    """Record an email reply."""
    service = get_service()
    
    reply = await service.record_reply(
        email_id,
        subject=request.subject,
        snippet=request.snippet,
        is_auto_reply=request.is_auto_reply,
        sentiment=request.sentiment,
        message_id=request.message_id
    )
    
    if not reply:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "id": reply.id,
        "replied_at": reply.replied_at.isoformat(),
    }


@router.post("/{email_id}/bounce")
async def record_bounce(email_id: str, request: RecordBounceRequest):
    """Record an email bounce."""
    service = get_service()
    
    try:
        bounce_type = BounceType(request.bounce_type)
    except ValueError:
        bounce_type = BounceType.SOFT
    
    bounce = await service.record_bounce(
        email_id,
        bounce_type=bounce_type,
        reason=request.reason,
        diagnostic_code=request.diagnostic_code
    )
    
    if not bounce:
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {
        "id": bounce.id,
        "bounce_type": bounce.bounce_type.value,
    }


@router.post("/{email_id}/unsubscribe")
async def record_unsubscribe(email_id: str):
    """Record an unsubscribe."""
    service = get_service()
    
    if not await service.record_unsubscribe(email_id):
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {"success": True}


@router.post("/{email_id}/complaint")
async def record_complaint(email_id: str):
    """Record a spam complaint."""
    service = get_service()
    
    if not await service.record_complaint(email_id):
        raise HTTPException(status_code=404, detail="Email not found")
    
    return {"success": True}


# Public tracking endpoints (for tracking pixel and links)
@router.get("/track/open/{tracking_id}")
async def track_open(
    tracking_id: str,
    response: Response
):
    """Tracking pixel endpoint - returns 1x1 transparent GIF."""
    service = get_service()
    
    await service.record_open(tracking_id)
    
    # Return 1x1 transparent GIF
    gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    
    return Response(
        content=gif,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.get("/track/click/{tracking_id}/{link_hash}")
async def track_click(
    tracking_id: str,
    link_hash: str,
    url: str
):
    """Track click and redirect."""
    service = get_service()
    
    await service.record_click(tracking_id, url)
    
    # Return redirect info (actual redirect would be done by frontend)
    return {"redirect_url": url}
