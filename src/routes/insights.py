"""
Insights Routes.

API endpoints for insights and recommendations.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter

from src.insights import get_insights_engine, InsightType, InsightPriority

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/")
async def get_insights(
    type: Optional[str] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """Get all insights."""
    engine = get_insights_engine()
    
    type_filter = None
    priority_filter = None
    
    if type:
        try:
            type_filter = InsightType(type)
        except ValueError:
            pass
    
    if priority:
        try:
            priority_filter = InsightPriority(priority)
        except ValueError:
            pass
    
    insights = engine.get_insights(
        insight_type=type_filter,
        priority=priority_filter,
    )
    
    return {
        "insights": insights,
        "count": len(insights),
    }


@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    """Get insights summary."""
    engine = get_insights_engine()
    return engine.get_summary()


@router.get("/high-priority")
async def get_high_priority() -> Dict[str, Any]:
    """Get high priority insights."""
    engine = get_insights_engine()
    insights = engine.get_high_priority_insights()
    
    return {
        "insights": insights,
        "count": len(insights),
    }


@router.post("/generate")
async def generate_insights() -> Dict[str, Any]:
    """Generate fresh insights."""
    engine = get_insights_engine()
    insights = await engine.generate_insights()
    
    return {
        "status": "success",
        "insights": [i.to_dict() for i in insights],
        "count": len(insights),
    }


@router.get("/types")
async def get_types() -> Dict[str, Any]:
    """Get available insight types."""
    return {
        "types": [
            {"id": t.value, "name": t.value.replace("_", " ").title()}
            for t in InsightType
        ],
    }
