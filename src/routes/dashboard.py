"""
Dashboard Routes.

API endpoints for dashboard metrics and real-time stats.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter

from src.dashboard import get_dashboard_aggregator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get all dashboard metrics."""
    aggregator = get_dashboard_aggregator()
    metrics = await aggregator.refresh_metrics()
    
    return {
        "metrics": metrics.to_dict(),
        "last_updated": aggregator.last_updated.isoformat() if aggregator.last_updated else None,
    }


@router.get("/quick-stats")
async def get_quick_stats() -> Dict[str, Any]:
    """Get quick stats for dashboard header."""
    aggregator = get_dashboard_aggregator()
    await aggregator.refresh_metrics()
    
    return aggregator.get_quick_stats()


@router.get("/pipeline")
async def get_pipeline() -> Dict[str, Any]:
    """Get pipeline summary."""
    aggregator = get_dashboard_aggregator()
    await aggregator.refresh_metrics()
    
    return {
        "stages": aggregator.get_pipeline_summary(),
    }


@router.get("/activity-feed")
async def get_activity_feed() -> Dict[str, Any]:
    """Get recent activity feed."""
    # This would pull from various sources
    activities = [
        {
            "type": "draft_sent",
            "message": "Draft sent to John Smith at Acme Corp",
            "timestamp": "2 min ago",
        },
        {
            "type": "reply_received",
            "message": "Reply from Sarah at TechCo",
            "timestamp": "15 min ago",
        },
        {
            "type": "meeting_scheduled",
            "message": "Meeting scheduled with VP at BigCorp",
            "timestamp": "1 hour ago",
        },
    ]
    
    return {
        "activities": activities,
    }


@router.post("/refresh")
async def refresh_metrics() -> Dict[str, Any]:
    """Force refresh all metrics."""
    aggregator = get_dashboard_aggregator()
    metrics = await aggregator.refresh_metrics()
    
    return {
        "status": "success",
        "metrics": metrics.to_dict(),
    }
