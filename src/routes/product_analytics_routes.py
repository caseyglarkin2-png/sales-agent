"""
Product Analytics Routes - Product usage and adoption analytics
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

router = APIRouter(prefix="/product-analytics", tags=["Product Analytics"])


class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    FEATURE_USE = "feature_use"
    BUTTON_CLICK = "button_click"
    FORM_SUBMIT = "form_submit"
    SEARCH = "search"
    ERROR = "error"
    CUSTOM = "custom"


class UserSegment(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    POWER = "power"
    AT_RISK = "at_risk"
    CHURNED = "churned"


class AdoptionStage(str, Enum):
    ONBOARDING = "onboarding"
    ACTIVATION = "activation"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"
    EXPANSION = "expansion"


# In-memory storage
events = {}
feature_usage = {}
user_analytics = {}
adoption_metrics = {}
funnels = {}


class EventTrack(BaseModel):
    event_type: EventType
    event_name: str
    properties: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None


class FunnelCreate(BaseModel):
    name: str
    steps: List[str]
    description: Optional[str] = None


# Event Tracking
@router.post("/events")
async def track_event(
    request: EventTrack,
    tenant_id: str = Query(default="default")
):
    """Track a product event"""
    event_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    event = {
        "id": event_id,
        "event_type": request.event_type.value,
        "event_name": request.event_name,
        "properties": request.properties or {},
        "user_id": request.user_id,
        "account_id": request.account_id,
        "tenant_id": tenant_id,
        "timestamp": now.isoformat()
    }
    
    events[event_id] = event
    
    return event


@router.get("/events")
async def list_events(
    event_type: Optional[EventType] = None,
    event_name: Optional[str] = None,
    user_id: Optional[str] = None,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List tracked events"""
    result = [e for e in events.values() if e.get("tenant_id") == tenant_id]
    
    if event_type:
        result = [e for e in result if e.get("event_type") == event_type.value]
    if event_name:
        result = [e for e in result if e.get("event_name") == event_name]
    if user_id:
        result = [e for e in result if e.get("user_id") == user_id]
    if account_id:
        result = [e for e in result if e.get("account_id") == account_id]
    if start_date:
        result = [e for e in result if e.get("timestamp", "") >= start_date]
    if end_date:
        result = [e for e in result if e.get("timestamp", "") <= end_date]
    
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"events": result[:limit], "total": len(result)}


@router.get("/events/count")
async def count_events(
    event_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: str = Query(default="day"),
    tenant_id: str = Query(default="default")
):
    """Count events over time"""
    # Simulate counts
    data_points = []
    days = 30
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()[:10]
        data_points.append({
            "date": date,
            "count": random.randint(50, 500)
        })
    
    return {
        "event_name": event_name,
        "group_by": group_by,
        "data": data_points,
        "total": sum(d["count"] for d in data_points)
    }


# Feature Usage
@router.get("/features")
async def get_feature_usage(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get feature usage analytics"""
    features = [
        "Dashboard", "Pipeline View", "Email Composer", "Sequences",
        "Reports", "Contacts", "Deals", "Analytics", "Integrations",
        "Team Management", "Settings", "Search"
    ]
    
    feature_stats = []
    for feature in features:
        feature_stats.append({
            "feature": feature,
            "total_uses": random.randint(100, 10000),
            "unique_users": random.randint(20, 200),
            "avg_uses_per_user": round(random.uniform(2, 15), 1),
            "adoption_rate": round(random.uniform(0.3, 0.95), 3),
            "trend": random.choice(["up", "down", "stable"]),
            "trend_pct": round(random.uniform(-20, 30), 1)
        })
    
    feature_stats.sort(key=lambda x: x["total_uses"], reverse=True)
    
    return {"features": feature_stats}


@router.get("/features/{feature_name}")
async def get_feature_details(
    feature_name: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get detailed feature analytics"""
    timeline = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()[:10]
        timeline.append({
            "date": date,
            "uses": random.randint(50, 300),
            "unique_users": random.randint(20, 100)
        })
    
    return {
        "feature": feature_name,
        "timeline": timeline,
        "summary": {
            "total_uses": sum(d["uses"] for d in timeline),
            "avg_daily_uses": round(sum(d["uses"] for d in timeline) / len(timeline), 1),
            "peak_day": max(timeline, key=lambda x: x["uses"]),
            "adoption_rate": round(random.uniform(0.4, 0.9), 3)
        },
        "user_segments": {
            "power_users": random.randint(10, 30),
            "regular_users": random.randint(30, 70),
            "occasional_users": random.randint(20, 50)
        }
    }


# User Analytics
@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get user activity analytics"""
    activity = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()[:10]
        activity.append({
            "date": date,
            "sessions": random.randint(0, 5),
            "events": random.randint(0, 100),
            "duration_minutes": random.randint(0, 120)
        })
    
    return {
        "user_id": user_id,
        "activity": activity,
        "summary": {
            "total_sessions": sum(d["sessions"] for d in activity),
            "total_events": sum(d["events"] for d in activity),
            "avg_session_duration": round(random.uniform(10, 45), 1),
            "most_used_features": ["Dashboard", "Pipeline", "Email"],
            "segment": random.choice([s.value for s in UserSegment])
        }
    }


@router.get("/users/segments")
async def get_user_segments(tenant_id: str = Query(default="default")):
    """Get user segment breakdown"""
    total_users = random.randint(100, 500)
    
    segments = {
        "new": {
            "count": int(total_users * random.uniform(0.1, 0.2)),
            "description": "Users in first 7 days"
        },
        "active": {
            "count": int(total_users * random.uniform(0.4, 0.5)),
            "description": "Active in last 7 days"
        },
        "power": {
            "count": int(total_users * random.uniform(0.1, 0.15)),
            "description": "Top 10% by usage"
        },
        "at_risk": {
            "count": int(total_users * random.uniform(0.1, 0.2)),
            "description": "Declining activity"
        },
        "churned": {
            "count": int(total_users * random.uniform(0.05, 0.15)),
            "description": "No activity in 30+ days"
        }
    }
    
    return {
        "total_users": total_users,
        "segments": segments
    }


# Adoption Metrics
@router.get("/adoption")
async def get_adoption_metrics(tenant_id: str = Query(default="default")):
    """Get product adoption metrics"""
    return {
        "activation_rate": round(random.uniform(0.5, 0.8), 3),
        "time_to_value_days": round(random.uniform(3, 14), 1),
        "feature_adoption_curve": {
            "week_1": round(random.uniform(0.3, 0.5), 3),
            "week_2": round(random.uniform(0.5, 0.7), 3),
            "week_4": round(random.uniform(0.6, 0.8), 3),
            "week_8": round(random.uniform(0.7, 0.9), 3)
        },
        "key_activation_events": [
            {"event": "first_pipeline_created", "completion_rate": round(random.uniform(0.6, 0.9), 3)},
            {"event": "first_email_sent", "completion_rate": round(random.uniform(0.5, 0.8), 3)},
            {"event": "first_deal_won", "completion_rate": round(random.uniform(0.3, 0.6), 3)},
            {"event": "integration_connected", "completion_rate": round(random.uniform(0.4, 0.7), 3)}
        ],
        "stickiness": {
            "dau_mau": round(random.uniform(0.2, 0.5), 3),
            "wau_mau": round(random.uniform(0.4, 0.7), 3)
        }
    }


@router.get("/adoption/cohorts")
async def get_adoption_cohorts(months: int = Query(default=6, ge=3, le=12)):
    """Get cohort adoption analysis"""
    cohorts = []
    
    for i in range(months):
        cohort_date = (datetime.utcnow() - timedelta(days=30 * (months - i))).isoformat()[:7]
        
        retention = []
        for week in range(min(4, i + 1)):
            retention.append({
                "week": week,
                "retention_rate": round(random.uniform(0.3, 0.9) * (1 - week * 0.1), 3)
            })
        
        cohorts.append({
            "cohort": cohort_date,
            "users": random.randint(20, 100),
            "retention": retention
        })
    
    return {"cohorts": cohorts}


# Funnels
@router.post("/funnels")
async def create_funnel(
    request: FunnelCreate,
    tenant_id: str = Query(default="default")
):
    """Create a funnel"""
    funnel_id = str(uuid.uuid4())
    
    funnel = {
        "id": funnel_id,
        "name": request.name,
        "steps": request.steps,
        "description": request.description,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    funnels[funnel_id] = funnel
    
    return funnel


@router.get("/funnels")
async def list_funnels(tenant_id: str = Query(default="default")):
    """List funnels"""
    result = [f for f in funnels.values() if f.get("tenant_id") == tenant_id]
    return {"funnels": result, "total": len(result)}


@router.get("/funnels/{funnel_id}/analysis")
async def analyze_funnel(
    funnel_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Analyze funnel conversion"""
    if funnel_id not in funnels:
        raise HTTPException(status_code=404, detail="Funnel not found")
    
    funnel = funnels[funnel_id]
    steps = funnel["steps"]
    
    analysis = []
    users = random.randint(500, 2000)
    
    for i, step in enumerate(steps):
        drop_rate = random.uniform(0.1, 0.4)
        users = int(users * (1 - drop_rate))
        
        analysis.append({
            "step": step,
            "order": i + 1,
            "users": users,
            "conversion_rate": round(1 - drop_rate if i > 0 else 1, 3),
            "drop_off": int(users * drop_rate / (1 - drop_rate)) if drop_rate < 1 else 0
        })
    
    return {
        "funnel_id": funnel_id,
        "name": funnel["name"],
        "analysis": analysis,
        "overall_conversion": round(analysis[-1]["users"] / analysis[0]["users"], 4)
    }


# Retention
@router.get("/retention")
async def get_retention_metrics(
    period: str = Query(default="weekly"),
    tenant_id: str = Query(default="default")
):
    """Get retention metrics"""
    if period == "weekly":
        periods = 12
        period_label = "Week"
    else:
        periods = 12
        period_label = "Month"
    
    retention_curve = []
    for i in range(periods):
        retention_rate = max(0.1, 0.9 - (i * 0.05) + random.uniform(-0.05, 0.05))
        retention_curve.append({
            "period": f"{period_label} {i}",
            "retention_rate": round(retention_rate, 3),
            "users_retained": int(1000 * retention_rate)
        })
    
    return {
        "period_type": period,
        "retention_curve": retention_curve,
        "summary": {
            "day_1_retention": round(random.uniform(0.7, 0.9), 3),
            "day_7_retention": round(random.uniform(0.4, 0.6), 3),
            "day_30_retention": round(random.uniform(0.2, 0.4), 3),
            "churn_rate_monthly": round(random.uniform(0.02, 0.08), 3)
        }
    }


# Health Score
@router.get("/accounts/{account_id}/health")
async def get_account_health(account_id: str):
    """Get account health score"""
    health_factors = {
        "usage_frequency": random.randint(40, 100),
        "feature_adoption": random.randint(30, 90),
        "user_engagement": random.randint(35, 95),
        "support_tickets": random.randint(50, 100),
        "nps_score": random.randint(40, 100)
    }
    
    overall = int(sum(health_factors.values()) / len(health_factors))
    
    return {
        "account_id": account_id,
        "health_score": overall,
        "health_factors": health_factors,
        "status": "healthy" if overall >= 70 else "at_risk" if overall >= 50 else "critical",
        "trend": random.choice(["improving", "stable", "declining"]),
        "recommendations": [
            "Increase feature adoption through targeted onboarding",
            "Schedule quarterly business review"
        ] if overall < 70 else []
    }


# Dashboard
@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get analytics dashboard"""
    return {
        "active_users": {
            "dau": random.randint(50, 200),
            "wau": random.randint(150, 400),
            "mau": random.randint(300, 800)
        },
        "engagement": {
            "avg_session_duration_minutes": round(random.uniform(10, 45), 1),
            "sessions_per_user": round(random.uniform(3, 15), 1),
            "events_per_session": round(random.uniform(20, 80), 1)
        },
        "top_features": [
            {"name": "Dashboard", "uses": random.randint(1000, 5000)},
            {"name": "Pipeline", "uses": random.randint(800, 4000)},
            {"name": "Email", "uses": random.randint(600, 3000)}
        ],
        "growth": {
            "new_users": random.randint(20, 100),
            "churned_users": random.randint(5, 30),
            "net_growth": random.randint(-10, 70)
        },
        "period_days": days
    }
