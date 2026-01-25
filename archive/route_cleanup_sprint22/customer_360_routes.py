"""
Customer 360 Routes - Unified customer view and insights
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

router = APIRouter(prefix="/customer-360", tags=["Customer 360"])


class CustomerSegment(str, Enum):
    ENTERPRISE = "enterprise"
    MID_MARKET = "mid_market"
    SMB = "smb"
    STARTUP = "startup"
    GOVERNMENT = "government"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    CHURNED = "churned"
    NEW = "new"


class RelationshipStage(str, Enum):
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    PARTNER = "partner"
    CHURNED = "churned"
    WIN_BACK = "win_back"


class TouchpointType(str, Enum):
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    SUPPORT_TICKET = "support_ticket"
    NPS_SURVEY = "nps_survey"
    PRODUCT_USAGE = "product_usage"
    BILLING = "billing"
    MARKETING = "marketing"
    SOCIAL = "social"


class SentimentScore(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


# In-memory storage
customer_profiles = {}
customer_touchpoints = {}
customer_metrics = {}
relationship_maps = {}
customer_notes = {}
customer_tasks = {}
customer_insights = {}
customer_journeys = {}


# Customer Profile
@router.post("/profiles")
async def create_customer_profile(
    account_id: str,
    account_name: str,
    segment: CustomerSegment,
    industry: Optional[str] = None,
    employee_count: Optional[int] = None,
    annual_revenue: Optional[float] = None,
    website: Optional[str] = None,
    primary_contact_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a customer 360 profile"""
    profile_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    profile = {
        "id": profile_id,
        "account_id": account_id,
        "account_name": account_name,
        "segment": segment.value,
        "industry": industry,
        "employee_count": employee_count,
        "annual_revenue": annual_revenue,
        "website": website,
        "primary_contact_id": primary_contact_id,
        "relationship_stage": RelationshipStage.PROSPECT.value,
        "health_status": HealthStatus.NEW.value,
        "health_score": 50,
        "nps_score": None,
        "lifetime_value": 0,
        "total_revenue": 0,
        "first_purchase_date": None,
        "last_activity_date": now.isoformat(),
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    customer_profiles[profile_id] = profile
    
    logger.info("customer_profile_created", profile_id=profile_id, account_name=account_name)
    return profile


@router.get("/profiles")
async def list_customer_profiles(
    segment: Optional[CustomerSegment] = None,
    health_status: Optional[HealthStatus] = None,
    relationship_stage: Optional[RelationshipStage] = None,
    min_health_score: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List customer profiles"""
    result = [p for p in customer_profiles.values() if p.get("tenant_id") == tenant_id]
    
    if segment:
        result = [p for p in result if p.get("segment") == segment.value]
    if health_status:
        result = [p for p in result if p.get("health_status") == health_status.value]
    if relationship_stage:
        result = [p for p in result if p.get("relationship_stage") == relationship_stage.value]
    if min_health_score is not None:
        result = [p for p in result if p.get("health_score", 0) >= min_health_score]
    if search:
        search_lower = search.lower()
        result = [p for p in result if search_lower in p.get("account_name", "").lower()]
    
    result.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)
    
    return {
        "profiles": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/profiles/{profile_id}")
async def get_customer_profile(profile_id: str):
    """Get complete customer 360 view"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = customer_profiles[profile_id]
    account_id = profile.get("account_id")
    
    # Gather all related data
    touchpoints = [t for t in customer_touchpoints.values() if t.get("account_id") == account_id]
    notes = [n for n in customer_notes.values() if n.get("account_id") == account_id]
    tasks = [t for t in customer_tasks.values() if t.get("account_id") == account_id]
    insights = customer_insights.get(account_id, [])
    
    # Generate metrics summary
    metrics = generate_customer_metrics(account_id)
    
    return {
        **profile,
        "metrics": metrics,
        "recent_touchpoints": sorted(touchpoints, key=lambda x: x.get("timestamp", ""), reverse=True)[:10],
        "notes": sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)[:5],
        "open_tasks": [t for t in tasks if t.get("status") != "completed"][:5],
        "insights": insights,
        "relationships": relationship_maps.get(account_id, []),
        "journey_stage": get_journey_stage(account_id)
    }


@router.get("/profiles/{profile_id}/timeline")
async def get_customer_timeline(
    profile_id: str,
    touchpoint_type: Optional[TouchpointType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get customer activity timeline"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    account_id = customer_profiles[profile_id].get("account_id")
    touchpoints = [t for t in customer_touchpoints.values() if t.get("account_id") == account_id]
    
    if touchpoint_type:
        touchpoints = [t for t in touchpoints if t.get("type") == touchpoint_type.value]
    if start_date:
        touchpoints = [t for t in touchpoints if t.get("timestamp", "") >= start_date]
    if end_date:
        touchpoints = [t for t in touchpoints if t.get("timestamp", "") <= end_date]
    
    touchpoints.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "profile_id": profile_id,
        "timeline": touchpoints[:limit],
        "total": len(touchpoints)
    }


# Touchpoints
@router.post("/touchpoints")
async def record_touchpoint(
    account_id: str,
    touchpoint_type: TouchpointType,
    subject: str,
    description: Optional[str] = None,
    sentiment: Optional[SentimentScore] = None,
    contact_id: Optional[str] = None,
    user_id: str = Query(default="default"),
    metadata: Optional[Dict[str, Any]] = None
):
    """Record a customer touchpoint"""
    touchpoint_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    touchpoint = {
        "id": touchpoint_id,
        "account_id": account_id,
        "type": touchpoint_type.value,
        "subject": subject,
        "description": description,
        "sentiment": sentiment.value if sentiment else None,
        "contact_id": contact_id,
        "user_id": user_id,
        "metadata": metadata or {},
        "timestamp": now.isoformat()
    }
    
    customer_touchpoints[touchpoint_id] = touchpoint
    
    # Update last activity date
    for profile in customer_profiles.values():
        if profile.get("account_id") == account_id:
            profile["last_activity_date"] = now.isoformat()
            break
    
    logger.info("touchpoint_recorded", touchpoint_id=touchpoint_id, type=touchpoint_type.value)
    return touchpoint


@router.get("/touchpoints")
async def list_touchpoints(
    account_id: Optional[str] = None,
    touchpoint_type: Optional[TouchpointType] = None,
    sentiment: Optional[SentimentScore] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List touchpoints"""
    result = list(customer_touchpoints.values())
    
    if account_id:
        result = [t for t in result if t.get("account_id") == account_id]
    if touchpoint_type:
        result = [t for t in result if t.get("type") == touchpoint_type.value]
    if sentiment:
        result = [t for t in result if t.get("sentiment") == sentiment.value]
    if start_date:
        result = [t for t in result if t.get("timestamp", "") >= start_date]
    if end_date:
        result = [t for t in result if t.get("timestamp", "") <= end_date]
    
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"touchpoints": result[:limit], "total": len(result)}


# Health Score
@router.get("/profiles/{profile_id}/health")
async def get_customer_health(profile_id: str):
    """Get detailed customer health analysis"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = customer_profiles[profile_id]
    
    health_factors = {
        "product_usage": {
            "score": random.randint(40, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.25
        },
        "engagement": {
            "score": random.randint(40, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.20
        },
        "support_tickets": {
            "score": random.randint(40, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.15
        },
        "nps": {
            "score": random.randint(40, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.15
        },
        "payment_history": {
            "score": random.randint(60, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.15
        },
        "relationship_depth": {
            "score": random.randint(40, 100),
            "trend": random.choice(["up", "down", "stable"]),
            "weight": 0.10
        }
    }
    
    overall_score = sum(f["score"] * f["weight"] for f in health_factors.values())
    
    # Determine status
    if overall_score >= 70:
        status = HealthStatus.HEALTHY.value
    elif overall_score >= 50:
        status = HealthStatus.AT_RISK.value
    else:
        status = HealthStatus.CRITICAL.value
    
    return {
        "profile_id": profile_id,
        "overall_score": round(overall_score),
        "status": status,
        "health_factors": health_factors,
        "recommendations": generate_health_recommendations(health_factors),
        "trend": random.choice(["improving", "declining", "stable"]),
        "calculated_at": datetime.utcnow().isoformat()
    }


@router.post("/profiles/{profile_id}/health/recalculate")
async def recalculate_health_score(profile_id: str):
    """Recalculate customer health score"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    health = await get_customer_health(profile_id)
    
    profile = customer_profiles[profile_id]
    profile["health_score"] = health["overall_score"]
    profile["health_status"] = health["status"]
    
    return health


# Relationships
@router.post("/profiles/{profile_id}/relationships")
async def add_relationship(
    profile_id: str,
    contact_id: str,
    contact_name: str,
    role: str,
    influence_level: str = "medium",
    sentiment: Optional[SentimentScore] = None,
    notes: Optional[str] = None
):
    """Add a relationship to customer profile"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    account_id = customer_profiles[profile_id].get("account_id")
    
    relationship = {
        "id": str(uuid.uuid4()),
        "contact_id": contact_id,
        "contact_name": contact_name,
        "role": role,
        "influence_level": influence_level,
        "sentiment": sentiment.value if sentiment else None,
        "notes": notes,
        "last_interaction": datetime.utcnow().isoformat(),
        "added_at": datetime.utcnow().isoformat()
    }
    
    if account_id not in relationship_maps:
        relationship_maps[account_id] = []
    
    relationship_maps[account_id].append(relationship)
    
    return relationship


@router.get("/profiles/{profile_id}/relationships")
async def get_relationships(profile_id: str):
    """Get customer relationships/org chart"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    account_id = customer_profiles[profile_id].get("account_id")
    relationships = relationship_maps.get(account_id, [])
    
    return {
        "profile_id": profile_id,
        "relationships": relationships,
        "total": len(relationships),
        "influence_map": generate_influence_map(relationships)
    }


# Notes
@router.post("/profiles/{profile_id}/notes")
async def add_note(
    profile_id: str,
    content: str,
    note_type: str = "general",
    visibility: str = "team",
    user_id: str = Query(default="default")
):
    """Add a note to customer profile"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    note_id = str(uuid.uuid4())
    account_id = customer_profiles[profile_id].get("account_id")
    now = datetime.utcnow()
    
    note = {
        "id": note_id,
        "account_id": account_id,
        "content": content,
        "note_type": note_type,
        "visibility": visibility,
        "created_by": user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    customer_notes[note_id] = note
    
    return note


@router.get("/profiles/{profile_id}/notes")
async def get_notes(
    profile_id: str,
    note_type: Optional[str] = None,
    limit: int = Query(default=20, le=50)
):
    """Get customer notes"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    account_id = customer_profiles[profile_id].get("account_id")
    notes = [n for n in customer_notes.values() if n.get("account_id") == account_id]
    
    if note_type:
        notes = [n for n in notes if n.get("note_type") == note_type]
    
    notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"notes": notes[:limit], "total": len(notes)}


# Tasks
@router.post("/profiles/{profile_id}/tasks")
async def create_task(
    profile_id: str,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "medium",
    assigned_to: Optional[str] = None,
    user_id: str = Query(default="default")
):
    """Create a task for customer"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    task_id = str(uuid.uuid4())
    account_id = customer_profiles[profile_id].get("account_id")
    now = datetime.utcnow()
    
    task = {
        "id": task_id,
        "account_id": account_id,
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "assigned_to": assigned_to or user_id,
        "status": "open",
        "created_by": user_id,
        "created_at": now.isoformat()
    }
    
    customer_tasks[task_id] = task
    
    return task


@router.get("/profiles/{profile_id}/tasks")
async def get_tasks(
    profile_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    """Get customer tasks"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    account_id = customer_profiles[profile_id].get("account_id")
    tasks = [t for t in customer_tasks.values() if t.get("account_id") == account_id]
    
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
    
    tasks.sort(key=lambda x: x.get("due_date", "9999"))
    
    return {"tasks": tasks, "total": len(tasks)}


# Insights
@router.get("/profiles/{profile_id}/insights")
async def get_customer_insights(profile_id: str):
    """Get AI-generated customer insights"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = customer_profiles[profile_id]
    
    insights = [
        {
            "type": "opportunity",
            "title": "Expansion opportunity detected",
            "description": "Customer usage has grown 45% in the last quarter. Consider upsell conversation.",
            "confidence": 0.85,
            "recommended_action": "Schedule expansion discussion"
        },
        {
            "type": "risk",
            "title": "Champion leaving company",
            "description": "Key contact has updated LinkedIn indicating job change. Develop new relationships.",
            "confidence": 0.78,
            "recommended_action": "Identify new stakeholders"
        },
        {
            "type": "engagement",
            "title": "Low recent engagement",
            "description": "No meetings or calls in the last 45 days. Proactive outreach recommended.",
            "confidence": 0.92,
            "recommended_action": "Schedule check-in call"
        },
        {
            "type": "sentiment",
            "title": "Recent support escalation",
            "description": "Customer opened a critical support ticket last week. Follow up on resolution.",
            "confidence": 0.88,
            "recommended_action": "Review ticket status"
        }
    ]
    
    return {
        "profile_id": profile_id,
        "insights": random.sample(insights, k=min(len(insights), 3)),
        "generated_at": datetime.utcnow().isoformat()
    }


# Journey
@router.get("/profiles/{profile_id}/journey")
async def get_customer_journey(profile_id: str):
    """Get customer journey visualization"""
    if profile_id not in customer_profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = customer_profiles[profile_id]
    
    stages = [
        {
            "stage": "Discovery",
            "status": "completed",
            "entered_at": (datetime.utcnow() - timedelta(days=180)).isoformat(),
            "completed_at": (datetime.utcnow() - timedelta(days=150)).isoformat(),
            "key_events": ["First website visit", "Downloaded whitepaper"]
        },
        {
            "stage": "Evaluation",
            "status": "completed",
            "entered_at": (datetime.utcnow() - timedelta(days=150)).isoformat(),
            "completed_at": (datetime.utcnow() - timedelta(days=120)).isoformat(),
            "key_events": ["Demo scheduled", "Technical review", "Proposal sent"]
        },
        {
            "stage": "Purchase",
            "status": "completed",
            "entered_at": (datetime.utcnow() - timedelta(days=120)).isoformat(),
            "completed_at": (datetime.utcnow() - timedelta(days=90)).isoformat(),
            "key_events": ["Contract signed", "First payment"]
        },
        {
            "stage": "Onboarding",
            "status": "completed",
            "entered_at": (datetime.utcnow() - timedelta(days=90)).isoformat(),
            "completed_at": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            "key_events": ["Kickoff call", "Training completed", "Go-live"]
        },
        {
            "stage": "Adoption",
            "status": "in_progress",
            "entered_at": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            "completed_at": None,
            "key_events": ["First value milestone", "Feature adoption increasing"]
        },
        {
            "stage": "Expansion",
            "status": "upcoming",
            "entered_at": None,
            "completed_at": None,
            "key_events": []
        }
    ]
    
    return {
        "profile_id": profile_id,
        "journey_stages": stages,
        "current_stage": "Adoption",
        "days_as_customer": 90,
        "next_milestone": "Quarterly business review"
    }


# Segment Analytics
@router.get("/analytics/segments")
async def get_segment_analytics(tenant_id: str = Query(default="default")):
    """Get analytics by customer segment"""
    tenant_profiles = [p for p in customer_profiles.values() if p.get("tenant_id") == tenant_id]
    
    segments = {}
    for segment in CustomerSegment:
        segment_profiles = [p for p in tenant_profiles if p.get("segment") == segment.value]
        
        segments[segment.value] = {
            "count": len(segment_profiles),
            "total_revenue": sum(p.get("total_revenue", 0) for p in segment_profiles),
            "avg_health_score": sum(p.get("health_score", 50) for p in segment_profiles) / max(1, len(segment_profiles)),
            "at_risk_count": len([p for p in segment_profiles if p.get("health_status") in ["at_risk", "critical"]])
        }
    
    return {
        "segments": segments,
        "total_customers": len(tenant_profiles),
        "overall_health_score": sum(p.get("health_score", 50) for p in tenant_profiles) / max(1, len(tenant_profiles))
    }


@router.get("/analytics/health-distribution")
async def get_health_distribution(tenant_id: str = Query(default="default")):
    """Get health status distribution"""
    tenant_profiles = [p for p in customer_profiles.values() if p.get("tenant_id") == tenant_id]
    
    distribution = {
        status.value: len([p for p in tenant_profiles if p.get("health_status") == status.value])
        for status in HealthStatus
    }
    
    return {
        "distribution": distribution,
        "total": len(tenant_profiles),
        "avg_health_score": sum(p.get("health_score", 50) for p in tenant_profiles) / max(1, len(tenant_profiles))
    }


# Helper functions
def generate_customer_metrics(account_id: str) -> Dict:
    """Generate customer metrics summary"""
    return {
        "mrr": random.randint(5000, 50000),
        "arr": random.randint(60000, 600000),
        "lifetime_value": random.randint(100000, 1000000),
        "nps_score": random.randint(-20, 80),
        "csat_score": round(random.uniform(3.5, 5.0), 1),
        "product_usage_score": random.randint(40, 100),
        "active_users": random.randint(10, 200),
        "support_tickets_open": random.randint(0, 5),
        "support_tickets_30d": random.randint(0, 10),
        "days_since_last_contact": random.randint(1, 60)
    }


def get_journey_stage(account_id: str) -> Dict:
    """Get current journey stage"""
    stages = ["discovery", "evaluation", "purchase", "onboarding", "adoption", "expansion", "renewal"]
    current = random.choice(stages[2:])
    
    return {
        "current": current,
        "progress_pct": random.uniform(0.3, 0.9),
        "next_stage": stages[stages.index(current) + 1] if current != "renewal" else None
    }


def generate_health_recommendations(factors: Dict) -> List[Dict]:
    """Generate health improvement recommendations"""
    recommendations = []
    
    for factor, data in factors.items():
        if data["score"] < 60:
            recommendations.append({
                "factor": factor,
                "priority": "high" if data["score"] < 40 else "medium",
                "recommendation": f"Improve {factor.replace('_', ' ')} - current score is low",
                "suggested_actions": [
                    f"Review {factor} trends",
                    "Schedule customer touchpoint",
                    "Create improvement plan"
                ]
            })
    
    return recommendations[:3]


def generate_influence_map(relationships: List[Dict]) -> Dict:
    """Generate influence map from relationships"""
    return {
        "total_contacts": len(relationships),
        "by_influence": {
            "high": len([r for r in relationships if r.get("influence_level") == "high"]),
            "medium": len([r for r in relationships if r.get("influence_level") == "medium"]),
            "low": len([r for r in relationships if r.get("influence_level") == "low"])
        },
        "sentiment_distribution": {
            "positive": len([r for r in relationships if r.get("sentiment") in ["positive", "very_positive"]]),
            "neutral": len([r for r in relationships if r.get("sentiment") == "neutral"]),
            "negative": len([r for r in relationships if r.get("sentiment") in ["negative", "very_negative"]])
        }
    }
