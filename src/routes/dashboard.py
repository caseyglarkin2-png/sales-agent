"""
Dashboard Routes.

API endpoints for dashboard metrics and real-time stats.
Sprint 43: Dashboard Intelligence & Metrics
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard import get_dashboard_aggregator
from src.db import get_db
from src.services.dashboard_metrics import DashboardMetricsService

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


# =============================================================================
# Sprint 43: Dashboard Intelligence Endpoints
# =============================================================================

@router.get("/today")
async def get_today_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get today's key metrics for dashboard.
    
    Sprint 43.1: Central metrics endpoint returning:
    - pending_actions: Count of items awaiting approval
    - approved_today: Count of items approved today
    - sent_today: Count of items sent today
    - failed_today: Count of failed executions today
    - agent_executions_24h: Total agent runs in last 24h
    - success_rate: Percentage of successful executions
    """
    service = DashboardMetricsService(db)
    return await service.get_today_metrics()


@router.get("/priority-queue")
async def get_priority_queue(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get top priority queue items by APS score.
    
    Sprint 43.2: Returns top items for quick action.
    """
    service = DashboardMetricsService(db)
    items = await service.get_top_priority_items(limit=limit)
    return {
        "items": items,
        "count": len(items),
    }


@router.get("/agent-performance")
async def get_agent_performance(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get agent performance summary.
    
    Sprint 43.3: Returns most active, highest success rate, and most failed agents.
    """
    service = DashboardMetricsService(db)
    return await service.get_agent_performance(hours=hours)


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get recent activity feed combining queue and executions.
    
    Sprint 43: Live activity stream for dashboard.
    """
    service = DashboardMetricsService(db)
    activities = await service.get_recent_activity(limit=limit)
    return {
        "activities": activities,
        "count": len(activities),
    }


@router.get("/pipeline-health")
async def get_pipeline_health() -> Dict[str, Any]:
    """
    Get HubSpot pipeline health summary.
    
    Sprint 43.4: Returns deal stages with counts, values, and at-risk deals.
    """
    from src.connectors.hubspot import get_hubspot_connector
    
    connector = get_hubspot_connector()
    if not connector:
        return {
            "error": "HubSpot not configured",
            "stages": [],
            "total_deals": 0,
            "total_value": 0,
        }
    
    try:
        summary = await connector.get_pipeline_summary()
        return summary
    except Exception as e:
        logger.error(f"Error fetching pipeline health: {e}")
        return {
            "error": str(e),
            "stages": [],
            "total_deals": 0,
            "total_value": 0,
        }
