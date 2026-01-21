"""
Analytics API Routes.

Endpoints for tracking and retrieving engagement metrics.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.analytics import get_analytics_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class TrackEventRequest(BaseModel):
    event_type: str  # sent, opened, clicked, replied, bounced, meeting
    contact_email: str
    campaign_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    """Get overall analytics summary."""
    engine = get_analytics_engine()
    return engine.get_summary_metrics()


@router.get("/daily")
async def get_daily_stats(days: int = 7) -> Dict[str, Any]:
    """Get daily statistics."""
    engine = get_analytics_engine()
    stats = engine.get_daily_stats(days=days)
    
    return {
        "daily_stats": stats,
        "days": days,
    }


@router.get("/campaigns")
async def get_campaigns(campaign_id: Optional[str] = None) -> Dict[str, Any]:
    """Get campaign metrics."""
    engine = get_analytics_engine()
    metrics = engine.get_campaign_metrics(campaign_id=campaign_id)
    
    return {
        "campaigns": metrics,
        "total": len(metrics),
    }


@router.get("/campaigns/top")
async def get_top_campaigns(
    limit: int = 5,
    sort_by: str = "reply_rate",
) -> Dict[str, Any]:
    """Get top performing campaigns."""
    engine = get_analytics_engine()
    campaigns = engine.get_top_performing_campaigns(limit=limit, sort_by=sort_by)
    
    return {
        "top_campaigns": campaigns,
        "sort_by": sort_by,
    }


@router.get("/contact/{email}")
async def get_contact_timeline(email: str) -> Dict[str, Any]:
    """Get engagement timeline for a contact."""
    engine = get_analytics_engine()
    timeline = engine.get_contact_timeline(email)
    
    return {
        "email": email,
        "events": timeline,
        "total_events": len(timeline),
    }


@router.post("/track")
async def track_event(request: TrackEventRequest) -> Dict[str, Any]:
    """Track an engagement event."""
    engine = get_analytics_engine()
    
    valid_events = ["sent", "opened", "clicked", "replied", "bounced", "meeting", "approved", "rejected"]
    if request.event_type not in valid_events:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {valid_events}")
    
    engine.track_event(
        event_type=request.event_type,
        contact_email=request.contact_email,
        campaign_id=request.campaign_id,
        metadata=request.metadata,
    )
    
    return {
        "status": "success",
        "message": f"Tracked {request.event_type} event for {request.contact_email}",
    }
