"""
AI Recommendations Routes - Intelligent Recommendations API
============================================================
REST API endpoints for AI-powered recommendations and insights.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel

from ..recommendations import (
    RecommendationsService,
    get_recommendations_service,
)
from ..recommendations.recommendations_service import (
    RecommendationType,
    RecommendationCategory,
    RecommendationPriority,
    RecommendationStatus,
    FeedbackType,
)


router = APIRouter(prefix="/recommendations", tags=["AI Recommendations"])


# Request models
class GenerateRecommendationsRequest(BaseModel):
    """Generate recommendations request."""
    types: Optional[list[str]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    limit: int = 10


class FeedbackRequest(BaseModel):
    """Feedback request."""
    feedback_type: str
    comment: Optional[str] = None


class DismissRequest(BaseModel):
    """Dismiss request."""
    reason: Optional[str] = None


def get_service() -> RecommendationsService:
    """Get recommendations service instance."""
    return get_recommendations_service()


# Enums
@router.get("/types")
async def list_recommendation_types():
    """List recommendation types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in RecommendationType
        ]
    }


@router.get("/categories")
async def list_categories():
    """List recommendation categories."""
    return {
        "categories": [
            {"value": c.value, "name": c.name}
            for c in RecommendationCategory
        ]
    }


@router.get("/priorities")
async def list_priorities():
    """List recommendation priorities."""
    return {
        "priorities": [
            {"value": p.value, "name": p.name}
            for p in RecommendationPriority
        ]
    }


# Generate recommendations
@router.post("/generate")
async def generate_recommendations(
    user_id: str,
    request: GenerateRecommendationsRequest,
):
    """Generate recommendations for a user."""
    service = get_service()
    
    types = None
    if request.types:
        types = []
        for t in request.types:
            try:
                types.append(RecommendationType(t))
            except ValueError:
                pass
    
    recs = await service.generate_recommendations(
        user_id=user_id,
        types=types,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        limit=request.limit,
    )
    
    return {
        "recommendations": [
            {
                "id": r.id,
                "type": r.type.value,
                "category": r.category.value,
                "priority": r.priority.value,
                "title": r.title,
                "description": r.description,
                "confidence": r.confidence,
                "impact_score": r.impact_score,
                "reasoning": r.reasoning,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "actions": [
                    {
                        "id": a.id,
                        "label": a.label,
                        "action_type": a.action_type,
                        "primary": a.primary,
                    }
                    for a in r.actions
                ],
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in recs
        ],
        "count": len(recs),
    }


@router.get("")
async def get_user_recommendations(
    user_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """Get recommendations for a user."""
    service = get_service()
    
    stat = None
    if status:
        try:
            stat = RecommendationStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    cat = None
    if category:
        try:
            cat = RecommendationCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
    
    pri = None
    if priority:
        try:
            pri = RecommendationPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority")
    
    recs = await service.get_user_recommendations(
        user_id=user_id,
        status=stat,
        category=cat,
        priority=pri,
        limit=limit,
    )
    
    return {
        "recommendations": [
            {
                "id": r.id,
                "type": r.type.value,
                "category": r.category.value,
                "priority": r.priority.value,
                "title": r.title,
                "description": r.description,
                "confidence": r.confidence,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in recs
        ],
        "count": len(recs),
    }


@router.get("/{rec_id}")
async def get_recommendation(rec_id: str):
    """Get a recommendation by ID."""
    service = get_service()
    rec = await service.get_recommendation(rec_id)
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    # Mark as viewed
    await service.mark_viewed(rec_id)
    
    return {
        "id": rec.id,
        "type": rec.type.value,
        "category": rec.category.value,
        "priority": rec.priority.value,
        "title": rec.title,
        "description": rec.description,
        "confidence": rec.confidence,
        "impact_score": rec.impact_score,
        "reasoning": rec.reasoning,
        "entity_type": rec.entity_type,
        "entity_id": rec.entity_id,
        "actions": [
            {
                "id": a.id,
                "label": a.label,
                "action_type": a.action_type,
                "action_data": a.action_data,
                "primary": a.primary,
            }
            for a in rec.actions
        ],
        "data": rec.data,
        "status": rec.status.value,
        "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
        "created_at": rec.created_at.isoformat(),
        "viewed_at": rec.viewed_at.isoformat() if rec.viewed_at else None,
    }


@router.post("/{rec_id}/accept")
async def accept_recommendation(rec_id: str, action_id: Optional[str] = None):
    """Accept a recommendation."""
    service = get_service()
    rec = await service.accept_recommendation(rec_id, action_id)
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return {"success": True, "status": rec.status.value}


@router.post("/{rec_id}/dismiss")
async def dismiss_recommendation(rec_id: str, request: DismissRequest):
    """Dismiss a recommendation."""
    service = get_service()
    rec = await service.dismiss_recommendation(rec_id, request.reason)
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return {"success": True, "status": rec.status.value}


@router.post("/{rec_id}/complete")
async def complete_recommendation(rec_id: str):
    """Mark a recommendation as completed."""
    service = get_service()
    rec = await service.complete_recommendation(rec_id)
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return {"success": True, "status": rec.status.value}


@router.post("/{rec_id}/feedback")
async def submit_feedback(rec_id: str, user_id: str, request: FeedbackRequest):
    """Submit feedback on a recommendation."""
    service = get_service()
    
    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid feedback type")
    
    feedback = await service.submit_feedback(
        rec_id=rec_id,
        user_id=user_id,
        feedback_type=feedback_type,
        comment=request.comment,
    )
    
    return {
        "feedback_id": feedback.id,
        "recommendation_id": feedback.recommendation_id,
        "feedback_type": feedback.feedback_type.value,
    }


# Entity-specific recommendations
@router.get("/deals/{deal_id}")
async def get_deal_recommendations(deal_id: str, user_id: str):
    """Get recommendations for a deal."""
    service = get_service()
    recs = await service.get_deal_recommendations(deal_id, user_id)
    
    return {
        "deal_id": deal_id,
        "recommendations": [
            {
                "id": r.id,
                "type": r.type.value,
                "title": r.title,
                "description": r.description,
                "priority": r.priority.value,
                "confidence": r.confidence,
            }
            for r in recs
        ],
    }


@router.get("/leads/{lead_id}")
async def get_lead_recommendations(lead_id: str, user_id: str):
    """Get recommendations for a lead."""
    service = get_service()
    recs = await service.get_lead_recommendations(lead_id, user_id)
    
    return {
        "lead_id": lead_id,
        "recommendations": [
            {
                "id": r.id,
                "type": r.type.value,
                "title": r.title,
                "description": r.description,
                "priority": r.priority.value,
                "confidence": r.confidence,
            }
            for r in recs
        ],
    }


@router.get("/accounts/{account_id}")
async def get_account_recommendations(account_id: str, user_id: str):
    """Get recommendations for an account."""
    service = get_service()
    recs = await service.get_account_recommendations(account_id, user_id)
    
    return {
        "account_id": account_id,
        "recommendations": [
            {
                "id": r.id,
                "type": r.type.value,
                "title": r.title,
                "description": r.description,
                "priority": r.priority.value,
                "confidence": r.confidence,
            }
            for r in recs
        ],
    }


# Insights
@router.get("/insights/coaching")
async def get_coaching_insights(user_id: str):
    """Get coaching insights for a user."""
    service = get_service()
    return await service.get_coaching_insights(user_id)


@router.get("/insights/pipeline")
async def get_pipeline_insights(user_id: str):
    """Get pipeline health insights."""
    service = get_service()
    insights = await service.get_pipeline_insights(user_id)
    
    return {
        "health_score": insights["health_score"],
        "trends": [
            {
                "metric": t.metric,
                "current_value": t.current_value,
                "previous_value": t.previous_value,
                "change_percent": t.change_percent,
                "trend_direction": t.trend_direction,
                "period": t.period,
                "insight": t.insight,
            }
            for t in insights["trends"]
        ],
        "risks": insights["risks"],
        "opportunities": insights["opportunities"],
    }


# Model management
@router.get("/models")
async def get_model_stats():
    """Get recommendation model statistics."""
    service = get_service()
    return {"models": await service.get_model_stats()}


@router.patch("/models/{model_id}")
async def toggle_model(model_id: str, enabled: bool):
    """Enable or disable a recommendation model."""
    service = get_service()
    result = await service.toggle_model(model_id, enabled)
    
    if not result:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return result
