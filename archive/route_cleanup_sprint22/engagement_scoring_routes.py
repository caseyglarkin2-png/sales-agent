"""
Engagement Scoring Routes - Multi-dimensional engagement tracking
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/engagement-scoring", tags=["Engagement Scoring"])


class EngagementLevel(str, Enum):
    COLD = "cold"
    WARMING = "warming"
    ENGAGED = "engaged"
    HIGHLY_ENGAGED = "highly_engaged"
    HOT = "hot"


class EngagementChannel(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    WEBSITE = "website"
    SOCIAL = "social"
    CONTENT = "content"
    EVENTS = "events"
    PRODUCT = "product"
    SUPPORT = "support"


class EntityType(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    OPPORTUNITY = "opportunity"


# In-memory storage
engagement_scores = {}
engagement_rules = {}
engagement_activities = {}
score_history = {}


class EngagementRuleCreate(BaseModel):
    name: str
    activity_type: str
    channel: EngagementChannel
    points: int
    decay_rate: float = 0.1  # Points decay per day
    max_per_day: Optional[int] = None
    multiplier: Optional[Dict[str, float]] = None  # Conditional multipliers


class ActivityRecordCreate(BaseModel):
    entity_type: EntityType
    entity_id: str
    activity_type: str
    channel: EngagementChannel
    points: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ScoreModelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    weights: Dict[str, float]  # Channel weights
    thresholds: Dict[str, int]  # Level thresholds
    decay_config: Optional[Dict[str, Any]] = None


# Score Calculation
@router.get("/score/{entity_type}/{entity_id}")
async def get_engagement_score(
    entity_type: EntityType,
    entity_id: str,
    tenant_id: str = Query(default="default")
):
    """Get engagement score for an entity"""
    score_key = f"{entity_type.value}_{entity_id}"
    
    # Return stored or generate mock score
    if score_key in engagement_scores:
        return engagement_scores[score_key]
    
    base_score = random.randint(20, 95)
    
    return {
        "entity_type": entity_type.value,
        "entity_id": entity_id,
        "overall_score": base_score,
        "level": _get_engagement_level(base_score),
        "trend": random.choice(["improving", "stable", "declining"]),
        "change_7d": random.randint(-10, 15),
        "breakdown": {
            "email": random.randint(0, 30),
            "website": random.randint(0, 25),
            "content": random.randint(0, 20),
            "events": random.randint(0, 15),
            "social": random.randint(0, 10)
        },
        "last_activity": (datetime.utcnow() - timedelta(days=random.randint(0, 7))).isoformat(),
        "activities_30d": random.randint(5, 50),
        "calculated_at": datetime.utcnow().isoformat()
    }


def _get_engagement_level(score: int) -> str:
    if score >= 80:
        return EngagementLevel.HOT.value
    elif score >= 60:
        return EngagementLevel.HIGHLY_ENGAGED.value
    elif score >= 40:
        return EngagementLevel.ENGAGED.value
    elif score >= 20:
        return EngagementLevel.WARMING.value
    else:
        return EngagementLevel.COLD.value


@router.post("/score/calculate")
async def calculate_engagement_score(
    entity_type: EntityType,
    entity_id: str,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Calculate or recalculate engagement score"""
    score_key = f"{entity_type.value}_{entity_id}"
    now = datetime.utcnow()
    
    # Get activities for entity
    entity_activities = [
        a for a in engagement_activities.values()
        if a.get("entity_id") == entity_id and a.get("entity_type") == entity_type.value
    ]
    
    # Calculate score based on activities
    total_points = sum(a.get("points", 0) for a in entity_activities)
    
    # Apply decay for older activities
    # (simplified for mock)
    base_score = min(100, total_points if total_points > 0 else random.randint(20, 80))
    
    score = {
        "entity_type": entity_type.value,
        "entity_id": entity_id,
        "overall_score": base_score,
        "level": _get_engagement_level(base_score),
        "trend": random.choice(["improving", "stable", "declining"]),
        "change_7d": random.randint(-10, 15),
        "breakdown": {
            "email": random.randint(0, 30),
            "website": random.randint(0, 25),
            "content": random.randint(0, 20),
            "events": random.randint(0, 15),
            "social": random.randint(0, 10)
        },
        "activities_count": len(entity_activities),
        "calculated_at": now.isoformat(),
        "tenant_id": tenant_id
    }
    
    engagement_scores[score_key] = score
    
    # Store in history
    history_key = f"{score_key}_{now.strftime('%Y-%m-%d')}"
    score_history[history_key] = {
        "score": base_score,
        "recorded_at": now.isoformat()
    }
    
    return score


# Activity Recording
@router.post("/activities")
async def record_activity(
    request: ActivityRecordCreate,
    tenant_id: str = Query(default="default")
):
    """Record an engagement activity"""
    activity_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get points from rules or use provided
    points = request.points
    if points is None:
        # Default points by activity type
        default_points = {
            "email_open": 5,
            "email_click": 10,
            "email_reply": 25,
            "page_view": 3,
            "form_submit": 30,
            "content_download": 15,
            "webinar_attend": 40,
            "meeting_attend": 50,
            "demo_request": 60,
            "phone_call": 20
        }
        points = default_points.get(request.activity_type, 10)
    
    activity = {
        "id": activity_id,
        "entity_type": request.entity_type.value,
        "entity_id": request.entity_id,
        "activity_type": request.activity_type,
        "channel": request.channel.value,
        "points": points,
        "metadata": request.metadata or {},
        "tenant_id": tenant_id,
        "recorded_at": now.isoformat()
    }
    
    engagement_activities[activity_id] = activity
    
    logger.info("engagement_activity_recorded", 
                activity_id=activity_id, 
                entity_id=request.entity_id,
                points=points)
    
    return activity


@router.get("/activities/{entity_type}/{entity_id}")
async def get_entity_activities(
    entity_type: EntityType,
    entity_id: str,
    channel: Optional[EngagementChannel] = None,
    days: int = Query(default=30, ge=1, le=90),
    tenant_id: str = Query(default="default")
):
    """Get activities for an entity"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    result = [
        a for a in engagement_activities.values()
        if a.get("entity_id") == entity_id 
        and a.get("entity_type") == entity_type.value
        and a.get("tenant_id") == tenant_id
    ]
    
    if channel:
        result = [a for a in result if a.get("channel") == channel.value]
    
    # Sort by recorded_at
    result = sorted(result, key=lambda x: x.get("recorded_at", ""), reverse=True)
    
    return {
        "activities": result,
        "total": len(result),
        "total_points": sum(a.get("points", 0) for a in result)
    }


# Scoring Rules
@router.post("/rules")
async def create_scoring_rule(
    request: EngagementRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create an engagement scoring rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "activity_type": request.activity_type,
        "channel": request.channel.value,
        "points": request.points,
        "decay_rate": request.decay_rate,
        "max_per_day": request.max_per_day,
        "multiplier": request.multiplier or {},
        "is_active": True,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    engagement_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_scoring_rules(
    channel: Optional[EngagementChannel] = None,
    active_only: bool = True,
    tenant_id: str = Query(default="default")
):
    """List engagement scoring rules"""
    result = [r for r in engagement_rules.values() if r.get("tenant_id") == tenant_id]
    
    if channel:
        result = [r for r in result if r.get("channel") == channel.value]
    if active_only:
        result = [r for r in result if r.get("is_active", True)]
    
    return {"rules": result, "total": len(result)}


@router.patch("/rules/{rule_id}")
async def update_scoring_rule(
    rule_id: str,
    updates: Dict[str, Any],
    tenant_id: str = Query(default="default")
):
    """Update a scoring rule"""
    if rule_id not in engagement_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = engagement_rules[rule_id]
    
    for key, value in updates.items():
        if key in ["points", "decay_rate", "max_per_day", "multiplier", "is_active"]:
            rule[key] = value
    
    return rule


# Leaderboards
@router.get("/leaderboard")
async def get_engagement_leaderboard(
    entity_type: EntityType = EntityType.CONTACT,
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Query(default="default")
):
    """Get engagement leaderboard"""
    # Generate mock leaderboard
    leaderboard = [
        {
            "rank": i + 1,
            "entity_id": f"{entity_type.value}_{uuid.uuid4().hex[:8]}",
            "name": f"Entity {i + 1}",
            "score": 95 - (i * 3) + random.randint(-2, 2),
            "level": _get_engagement_level(95 - (i * 3)),
            "trend": random.choice(["up", "down", "stable"]),
            "activities_7d": random.randint(5, 30)
        }
        for i in range(limit)
    ]
    
    return {"leaderboard": leaderboard, "entity_type": entity_type.value}


# Score History
@router.get("/history/{entity_type}/{entity_id}")
async def get_score_history(
    entity_type: EntityType,
    entity_id: str,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get historical engagement scores"""
    now = datetime.utcnow()
    history = []
    
    for i in range(days):
        date = now - timedelta(days=i)
        base_score = random.randint(50, 85)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "score": base_score + random.randint(-5, 5),
            "activities": random.randint(0, 10)
        })
    
    return {
        "entity_type": entity_type.value,
        "entity_id": entity_id,
        "history": list(reversed(history)),
        "avg_score": round(sum(h["score"] for h in history) / len(history), 1)
    }


# Segments
@router.get("/segments")
async def get_engagement_segments(
    entity_type: EntityType = EntityType.CONTACT,
    tenant_id: str = Query(default="default")
):
    """Get entities segmented by engagement level"""
    return {
        "entity_type": entity_type.value,
        "segments": [
            {
                "level": EngagementLevel.HOT.value,
                "count": random.randint(50, 150),
                "pct": round(random.uniform(0.05, 0.15), 3),
                "avg_score": random.randint(85, 95)
            },
            {
                "level": EngagementLevel.HIGHLY_ENGAGED.value,
                "count": random.randint(100, 300),
                "pct": round(random.uniform(0.15, 0.25), 3),
                "avg_score": random.randint(65, 79)
            },
            {
                "level": EngagementLevel.ENGAGED.value,
                "count": random.randint(200, 500),
                "pct": round(random.uniform(0.25, 0.35), 3),
                "avg_score": random.randint(45, 59)
            },
            {
                "level": EngagementLevel.WARMING.value,
                "count": random.randint(150, 400),
                "pct": round(random.uniform(0.20, 0.30), 3),
                "avg_score": random.randint(25, 39)
            },
            {
                "level": EngagementLevel.COLD.value,
                "count": random.randint(100, 300),
                "pct": round(random.uniform(0.10, 0.20), 3),
                "avg_score": random.randint(5, 19)
            }
        ],
        "total_entities": random.randint(800, 1500)
    }


# Analytics
@router.get("/analytics")
async def get_engagement_analytics(
    entity_type: EntityType = EntityType.CONTACT,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get engagement analytics"""
    return {
        "entity_type": entity_type.value,
        "period_days": days,
        "summary": {
            "avg_score": round(random.uniform(45, 65), 1),
            "median_score": random.randint(40, 60),
            "score_change": round(random.uniform(-5, 10), 1),
            "total_activities": random.randint(5000, 20000),
            "unique_entities_engaged": random.randint(500, 2000)
        },
        "by_channel": {
            "email": {"activities": random.randint(2000, 8000), "avg_points": round(random.uniform(8, 15), 1)},
            "website": {"activities": random.randint(1500, 6000), "avg_points": round(random.uniform(5, 10), 1)},
            "content": {"activities": random.randint(500, 2000), "avg_points": round(random.uniform(12, 20), 1)},
            "events": {"activities": random.randint(100, 500), "avg_points": round(random.uniform(30, 50), 1)},
            "social": {"activities": random.randint(200, 1000), "avg_points": round(random.uniform(5, 12), 1)}
        },
        "top_activities": [
            {"activity": "email_open", "count": random.randint(3000, 8000)},
            {"activity": "page_view", "count": random.randint(2000, 6000)},
            {"activity": "email_click", "count": random.randint(1000, 4000)},
            {"activity": "content_download", "count": random.randint(500, 2000)},
            {"activity": "meeting_attend", "count": random.randint(100, 500)}
        ],
        "trends": {
            "hot_entities_change": round(random.uniform(-10, 20), 1),
            "cold_entities_change": round(random.uniform(-15, 5), 1),
            "avg_activities_per_entity": round(random.uniform(5, 15), 1)
        }
    }


# Alerts
@router.get("/alerts")
async def get_engagement_alerts(
    tenant_id: str = Query(default="default")
):
    """Get engagement alerts for significant changes"""
    return {
        "alerts": [
            {
                "type": "score_spike",
                "entity_type": "contact",
                "entity_id": f"contact_{random.randint(100, 999)}",
                "message": "Engagement score increased by 25 points in 24 hours",
                "priority": "high",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "score_drop",
                "entity_type": "account",
                "entity_id": f"account_{random.randint(100, 999)}",
                "message": "Key account engagement dropped below threshold",
                "priority": "critical",
                "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat()
            },
            {
                "type": "reengagement",
                "entity_type": "contact",
                "entity_id": f"contact_{random.randint(100, 999)}",
                "message": "Previously cold contact showing renewed activity",
                "priority": "medium",
                "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat()
            }
        ]
    }


# Predictions
@router.get("/predict/{entity_type}/{entity_id}")
async def predict_engagement(
    entity_type: EntityType,
    entity_id: str,
    days_ahead: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Predict future engagement levels"""
    current_score = random.randint(40, 75)
    
    return {
        "entity_type": entity_type.value,
        "entity_id": entity_id,
        "current_score": current_score,
        "predictions": [
            {
                "days_from_now": 7,
                "predicted_score": current_score + random.randint(-5, 10),
                "confidence": round(random.uniform(0.75, 0.90), 2)
            },
            {
                "days_from_now": 14,
                "predicted_score": current_score + random.randint(-8, 12),
                "confidence": round(random.uniform(0.65, 0.85), 2)
            },
            {
                "days_from_now": 30,
                "predicted_score": current_score + random.randint(-10, 15),
                "confidence": round(random.uniform(0.55, 0.75), 2)
            }
        ],
        "churn_risk": round(random.uniform(0.05, 0.35), 2),
        "recommended_actions": [
            "Send personalized content",
            "Schedule check-in call",
            "Invite to upcoming webinar"
        ]
    }
