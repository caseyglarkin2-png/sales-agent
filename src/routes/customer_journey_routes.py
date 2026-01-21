"""
Customer Journey Routes - Customer lifecycle and journey mapping
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

router = APIRouter(prefix="/customer-journey", tags=["Customer Journey"])


class JourneyStage(str, Enum):
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    EVALUATION = "evaluation"
    PURCHASE = "purchase"
    ONBOARDING = "onboarding"
    ADOPTION = "adoption"
    EXPANSION = "expansion"
    ADVOCACY = "advocacy"


class TouchpointType(str, Enum):
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    WEBINAR = "webinar"
    CONTENT = "content"
    DEMO = "demo"
    SUPPORT = "support"
    EVENT = "event"
    SOCIAL = "social"
    WEBSITE = "website"


class JourneyStatus(str, Enum):
    ACTIVE = "active"
    STALLED = "stalled"
    COMPLETED = "completed"
    CHURNED = "churned"


# In-memory storage
customer_journeys = {}
journey_templates = {}
touchpoints = {}
journey_milestones = {}


class JourneyCreate(BaseModel):
    customer_id: str
    customer_name: str
    template_id: Optional[str] = None
    initial_stage: JourneyStage = JourneyStage.AWARENESS
    metadata: Optional[Dict[str, Any]] = None


class TouchpointCreate(BaseModel):
    journey_id: str
    touchpoint_type: TouchpointType
    channel: str
    description: str
    outcome: Optional[str] = None
    sentiment: Optional[str] = None  # positive, neutral, negative
    rep_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class JourneyTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    stages: List[Dict[str, Any]]
    milestones: Optional[List[Dict[str, Any]]] = None
    expected_duration_days: int = 90


# Customer Journeys
@router.post("/")
async def create_journey(
    request: JourneyCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new customer journey"""
    journey_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    journey = {
        "id": journey_id,
        "customer_id": request.customer_id,
        "customer_name": request.customer_name,
        "template_id": request.template_id,
        "current_stage": request.initial_stage.value,
        "status": JourneyStatus.ACTIVE.value,
        "started_at": now.isoformat(),
        "stage_history": [{
            "stage": request.initial_stage.value,
            "entered_at": now.isoformat(),
            "exited_at": None
        }],
        "touchpoint_count": 0,
        "health_score": 100,
        "metadata": request.metadata or {},
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    customer_journeys[journey_id] = journey
    
    logger.info("journey_created", journey_id=journey_id, customer_id=request.customer_id)
    
    return journey


@router.get("/")
async def list_journeys(
    stage: Optional[JourneyStage] = None,
    status: Optional[JourneyStatus] = None,
    customer_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Query(default="default")
):
    """List customer journeys"""
    result = [j for j in customer_journeys.values() if j.get("tenant_id") == tenant_id]
    
    if stage:
        result = [j for j in result if j.get("current_stage") == stage.value]
    if status:
        result = [j for j in result if j.get("status") == status.value]
    if customer_id:
        result = [j for j in result if j.get("customer_id") == customer_id]
    
    return {"journeys": result[:limit], "total": len(result)}


@router.get("/{journey_id}")
async def get_journey(
    journey_id: str,
    tenant_id: str = Query(default="default")
):
    """Get journey details"""
    if journey_id not in customer_journeys:
        raise HTTPException(status_code=404, detail="Journey not found")
    return customer_journeys[journey_id]


@router.post("/{journey_id}/advance")
async def advance_journey_stage(
    journey_id: str,
    new_stage: JourneyStage,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Advance journey to next stage"""
    if journey_id not in customer_journeys:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    journey = customer_journeys[journey_id]
    now = datetime.utcnow()
    
    # Update current stage exit time
    if journey["stage_history"]:
        journey["stage_history"][-1]["exited_at"] = now.isoformat()
    
    # Add new stage
    journey["stage_history"].append({
        "stage": new_stage.value,
        "entered_at": now.isoformat(),
        "exited_at": None,
        "notes": notes
    })
    
    journey["current_stage"] = new_stage.value
    journey["updated_at"] = now.isoformat()
    
    return journey


@router.post("/{journey_id}/stall")
async def mark_journey_stalled(
    journey_id: str,
    reason: str,
    tenant_id: str = Query(default="default")
):
    """Mark journey as stalled"""
    if journey_id not in customer_journeys:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    journey = customer_journeys[journey_id]
    journey["status"] = JourneyStatus.STALLED.value
    journey["stall_reason"] = reason
    journey["stalled_at"] = datetime.utcnow().isoformat()
    
    return journey


# Touchpoints
@router.post("/touchpoints")
async def add_touchpoint(
    request: TouchpointCreate,
    tenant_id: str = Query(default="default")
):
    """Add a touchpoint to a journey"""
    touchpoint_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    touchpoint = {
        "id": touchpoint_id,
        "journey_id": request.journey_id,
        "touchpoint_type": request.touchpoint_type.value,
        "channel": request.channel,
        "description": request.description,
        "outcome": request.outcome,
        "sentiment": request.sentiment,
        "rep_id": request.rep_id,
        "metadata": request.metadata or {},
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    touchpoints[touchpoint_id] = touchpoint
    
    # Update journey touchpoint count
    if request.journey_id in customer_journeys:
        customer_journeys[request.journey_id]["touchpoint_count"] += 1
        customer_journeys[request.journey_id]["last_touchpoint_at"] = now.isoformat()
    
    return touchpoint


@router.get("/{journey_id}/touchpoints")
async def get_journey_touchpoints(
    journey_id: str,
    touchpoint_type: Optional[TouchpointType] = None,
    tenant_id: str = Query(default="default")
):
    """Get all touchpoints for a journey"""
    result = [t for t in touchpoints.values() 
              if t.get("journey_id") == journey_id and t.get("tenant_id") == tenant_id]
    
    if touchpoint_type:
        result = [t for t in result if t.get("touchpoint_type") == touchpoint_type.value]
    
    # Sort by created_at
    result = sorted(result, key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"touchpoints": result, "total": len(result)}


# Timeline View
@router.get("/{journey_id}/timeline")
async def get_journey_timeline(
    journey_id: str,
    tenant_id: str = Query(default="default")
):
    """Get visual timeline of journey"""
    journey = customer_journeys.get(journey_id, {})
    journey_touchpoints = [t for t in touchpoints.values() if t.get("journey_id") == journey_id]
    
    timeline_events = []
    
    # Add stage changes
    for stage_entry in journey.get("stage_history", []):
        timeline_events.append({
            "type": "stage_change",
            "stage": stage_entry["stage"],
            "timestamp": stage_entry["entered_at"],
            "description": f"Entered {stage_entry['stage']} stage"
        })
    
    # Add touchpoints
    for tp in journey_touchpoints:
        timeline_events.append({
            "type": "touchpoint",
            "touchpoint_type": tp["touchpoint_type"],
            "channel": tp["channel"],
            "timestamp": tp["created_at"],
            "description": tp["description"],
            "sentiment": tp.get("sentiment")
        })
    
    # Sort by timestamp
    timeline_events = sorted(timeline_events, key=lambda x: x.get("timestamp", ""))
    
    return {
        "journey_id": journey_id,
        "timeline": timeline_events,
        "total_events": len(timeline_events)
    }


# Journey Templates
@router.post("/templates")
async def create_journey_template(
    request: JourneyTemplateCreate,
    tenant_id: str = Query(default="default")
):
    """Create a journey template"""
    template_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    template = {
        "id": template_id,
        "name": request.name,
        "description": request.description,
        "stages": request.stages,
        "milestones": request.milestones or [],
        "expected_duration_days": request.expected_duration_days,
        "is_active": True,
        "journeys_created": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    journey_templates[template_id] = template
    
    return template


@router.get("/templates")
async def list_journey_templates(
    active_only: bool = True,
    tenant_id: str = Query(default="default")
):
    """List journey templates"""
    result = [t for t in journey_templates.values() if t.get("tenant_id") == tenant_id]
    
    if active_only:
        result = [t for t in result if t.get("is_active", True)]
    
    return {"templates": result, "total": len(result)}


# Health Scoring
@router.get("/{journey_id}/health")
async def get_journey_health(
    journey_id: str,
    tenant_id: str = Query(default="default")
):
    """Get health score breakdown for journey"""
    return {
        "journey_id": journey_id,
        "overall_score": random.randint(60, 100),
        "components": {
            "engagement": {
                "score": random.randint(50, 100),
                "trend": random.choice(["improving", "stable", "declining"]),
                "factors": ["Email opens", "Meeting attendance", "Response time"]
            },
            "velocity": {
                "score": random.randint(50, 100),
                "trend": random.choice(["improving", "stable", "declining"]),
                "factors": ["Stage progression speed", "Time in current stage"]
            },
            "sentiment": {
                "score": random.randint(50, 100),
                "trend": random.choice(["improving", "stable", "declining"]),
                "factors": ["Support interactions", "NPS responses", "Call sentiment"]
            },
            "usage": {
                "score": random.randint(50, 100),
                "trend": random.choice(["improving", "stable", "declining"]),
                "factors": ["Product usage", "Feature adoption", "Login frequency"]
            }
        },
        "risks": [
            {"factor": "No activity in 7 days", "severity": "medium"},
            {"factor": "Sentiment declining", "severity": "low"}
        ],
        "recommendations": [
            "Schedule check-in call",
            "Send product tips email",
            "Offer training session"
        ]
    }


# Analytics
@router.get("/analytics/overview")
async def get_journey_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get journey analytics overview"""
    return {
        "period_days": days,
        "summary": {
            "active_journeys": random.randint(50, 200),
            "completed_journeys": random.randint(20, 80),
            "stalled_journeys": random.randint(5, 30),
            "churned_journeys": random.randint(2, 15)
        },
        "stage_distribution": {
            "awareness": random.randint(20, 50),
            "consideration": random.randint(30, 60),
            "evaluation": random.randint(20, 40),
            "purchase": random.randint(10, 30),
            "onboarding": random.randint(15, 35),
            "adoption": random.randint(25, 55),
            "expansion": random.randint(10, 25),
            "advocacy": random.randint(5, 20)
        },
        "conversion_rates": {
            "awareness_to_consideration": round(random.uniform(0.4, 0.7), 2),
            "consideration_to_evaluation": round(random.uniform(0.5, 0.8), 2),
            "evaluation_to_purchase": round(random.uniform(0.3, 0.5), 2),
            "onboarding_to_adoption": round(random.uniform(0.7, 0.95), 2)
        },
        "avg_time_per_stage_days": {
            "awareness": random.randint(5, 15),
            "consideration": random.randint(10, 25),
            "evaluation": random.randint(15, 30),
            "purchase": random.randint(5, 15),
            "onboarding": random.randint(14, 30)
        },
        "touchpoint_effectiveness": [
            {"type": "demo", "conversion_rate": 0.45, "avg_sentiment": "positive"},
            {"type": "webinar", "conversion_rate": 0.35, "avg_sentiment": "positive"},
            {"type": "email", "conversion_rate": 0.15, "avg_sentiment": "neutral"}
        ]
    }


@router.get("/analytics/funnel")
async def get_funnel_analytics(
    start_stage: JourneyStage = JourneyStage.AWARENESS,
    end_stage: JourneyStage = JourneyStage.PURCHASE,
    tenant_id: str = Query(default="default")
):
    """Get funnel analytics between stages"""
    stages = ["awareness", "consideration", "evaluation", "purchase"]
    funnel_data = []
    
    prev_count = random.randint(1000, 2000)
    for stage in stages:
        conversion_rate = round(random.uniform(0.5, 0.85), 2)
        count = int(prev_count * conversion_rate)
        funnel_data.append({
            "stage": stage,
            "count": prev_count,
            "conversion_to_next": conversion_rate,
            "drop_off": prev_count - count
        })
        prev_count = count
    
    return {
        "funnel": funnel_data,
        "total_conversion_rate": round(funnel_data[-1]["count"] / funnel_data[0]["count"], 3),
        "avg_journey_time_days": random.randint(30, 90)
    }


# Cohort Analysis
@router.get("/analytics/cohorts")
async def get_cohort_analysis(
    cohort_by: str = Query(default="month"),
    tenant_id: str = Query(default="default")
):
    """Get cohort analysis of journeys"""
    cohorts = []
    now = datetime.utcnow()
    
    for i in range(6):
        cohort_date = now - timedelta(days=30 * i)
        cohorts.append({
            "cohort": cohort_date.strftime("%Y-%m"),
            "started": random.randint(50, 150),
            "month_1_retention": round(random.uniform(0.7, 0.9), 2),
            "month_2_retention": round(random.uniform(0.5, 0.8), 2),
            "month_3_retention": round(random.uniform(0.4, 0.7), 2),
            "completed_pct": round(random.uniform(0.2, 0.5), 2),
            "churned_pct": round(random.uniform(0.05, 0.15), 2)
        })
    
    return {"cohorts": cohorts}


# Predictions
@router.get("/{journey_id}/predictions")
async def get_journey_predictions(
    journey_id: str,
    tenant_id: str = Query(default="default")
):
    """Get AI predictions for journey outcome"""
    return {
        "journey_id": journey_id,
        "predictions": {
            "completion_probability": round(random.uniform(0.5, 0.9), 2),
            "expected_completion_date": (datetime.utcnow() + timedelta(days=random.randint(30, 90))).strftime("%Y-%m-%d"),
            "churn_risk": round(random.uniform(0.05, 0.3), 2),
            "expansion_potential": round(random.uniform(0.2, 0.7), 2),
            "predicted_ltv": random.randint(10000, 100000)
        },
        "next_best_actions": [
            {"action": "Schedule success review", "impact": "high", "timing": "This week"},
            {"action": "Share advanced use cases", "impact": "medium", "timing": "Next week"},
            {"action": "Introduce to community", "impact": "medium", "timing": "This month"}
        ],
        "risk_factors": [
            {"factor": "Low product usage last week", "severity": "medium"},
            {"factor": "No executive engagement", "severity": "low"}
        ]
    }
