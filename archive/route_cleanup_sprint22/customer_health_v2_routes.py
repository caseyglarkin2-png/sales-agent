"""
Customer Health V2 Routes - Advanced customer health monitoring
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

router = APIRouter(prefix="/customer-health-v2", tags=["Customer Health V2"])


class HealthStatus(str, Enum):
    EXCELLENT = "excellent"
    HEALTHY = "healthy"
    NEUTRAL = "neutral"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class HealthCategory(str, Enum):
    PRODUCT_USAGE = "product_usage"
    SUPPORT = "support"
    RELATIONSHIP = "relationship"
    FINANCIAL = "financial"
    ENGAGEMENT = "engagement"
    ADOPTION = "adoption"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# In-memory storage
health_scores = {}
health_alerts = {}
health_metrics = {}
playbooks = {}


class HealthScoreModel(BaseModel):
    account_id: str
    account_name: Optional[str] = None
    custom_weights: Optional[Dict[str, float]] = None


class AlertCreate(BaseModel):
    account_id: str
    category: HealthCategory
    severity: AlertSeverity
    title: str
    description: Optional[str] = None
    recommended_action: Optional[str] = None


# Health Scores
@router.get("/accounts/{account_id}/health")
async def get_account_health(
    account_id: str,
    include_history: bool = Query(default=False)
):
    """Get comprehensive health score for an account"""
    now = datetime.utcnow()
    
    # Generate health factors
    factors = {}
    for category in HealthCategory:
        score = random.randint(30, 100)
        trend = random.choice([t.value for t in TrendDirection])
        
        factors[category.value] = {
            "score": score,
            "weight": round(random.uniform(0.1, 0.3), 2),
            "trend": trend,
            "trend_change": round(random.uniform(-15, 15), 1),
            "status": "excellent" if score >= 80 else "healthy" if score >= 60 else "at_risk" if score >= 40 else "critical"
        }
    
    # Calculate overall score
    total_weight = sum(f["weight"] for f in factors.values())
    overall_score = round(sum(f["score"] * f["weight"] for f in factors.values()) / total_weight)
    
    health = {
        "account_id": account_id,
        "overall_score": overall_score,
        "status": "excellent" if overall_score >= 80 else "healthy" if overall_score >= 60 else "at_risk" if overall_score >= 40 else "critical",
        "trend": random.choice([t.value for t in TrendDirection]),
        "factors": factors,
        "calculated_at": now.isoformat()
    }
    
    if include_history:
        history = []
        for i in range(30):
            date = (now - timedelta(days=30 - i)).isoformat()[:10]
            history.append({
                "date": date,
                "score": random.randint(max(40, overall_score - 20), min(100, overall_score + 20))
            })
        health["history"] = history
    
    # Add recommendations
    if overall_score < 70:
        health["recommendations"] = [
            {"priority": 1, "action": "Schedule executive business review"},
            {"priority": 2, "action": "Increase product training sessions"},
            {"priority": 3, "action": "Review support ticket resolution times"}
        ]
    
    return health


@router.get("/health/overview")
async def get_health_overview(
    status: Optional[HealthStatus] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get health overview for all accounts"""
    accounts = []
    
    for i in range(20):
        score = random.randint(30, 100)
        status_val = "excellent" if score >= 80 else "healthy" if score >= 60 else "at_risk" if score >= 40 else "critical"
        
        accounts.append({
            "account_id": f"acc_{i+1}",
            "account_name": f"Account {i+1}",
            "score": score,
            "status": status_val,
            "trend": random.choice([t.value for t in TrendDirection]),
            "arr": random.randint(10000, 500000),
            "last_activity": (datetime.utcnow() - timedelta(days=random.randint(0, 30))).isoformat()
        })
    
    if status:
        accounts = [a for a in accounts if a["status"] == status.value]
    
    accounts.sort(key=lambda x: x["score"])
    
    return {
        "accounts": accounts[:limit],
        "summary": {
            "excellent": len([a for a in accounts if a["status"] == "excellent"]),
            "healthy": len([a for a in accounts if a["status"] == "healthy"]),
            "at_risk": len([a for a in accounts if a["status"] == "at_risk"]),
            "critical": len([a for a in accounts if a["status"] == "critical"]),
            "avg_score": round(sum(a["score"] for a in accounts) / len(accounts)) if accounts else 0
        }
    }


@router.post("/health/calculate")
async def calculate_health_score(
    request: HealthScoreModel,
    tenant_id: str = Query(default="default")
):
    """Calculate health score for an account with custom weights"""
    weights = request.custom_weights or {
        "product_usage": 0.25,
        "support": 0.15,
        "relationship": 0.20,
        "financial": 0.20,
        "engagement": 0.10,
        "adoption": 0.10
    }
    
    scores = {}
    for category, weight in weights.items():
        scores[category] = {
            "raw_score": random.randint(40, 100),
            "weight": weight
        }
    
    total_weight = sum(s["weight"] for s in scores.values())
    overall = round(sum(s["raw_score"] * s["weight"] for s in scores.values()) / total_weight)
    
    result = {
        "account_id": request.account_id,
        "overall_score": overall,
        "status": "excellent" if overall >= 80 else "healthy" if overall >= 60 else "at_risk" if overall >= 40 else "critical",
        "category_scores": scores,
        "calculated_at": datetime.utcnow().isoformat()
    }
    
    health_scores[request.account_id] = result
    
    return result


# Alerts
@router.post("/alerts")
async def create_health_alert(
    request: AlertCreate,
    tenant_id: str = Query(default="default")
):
    """Create a health alert"""
    alert_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    alert = {
        "id": alert_id,
        "account_id": request.account_id,
        "category": request.category.value,
        "severity": request.severity.value,
        "title": request.title,
        "description": request.description,
        "recommended_action": request.recommended_action,
        "status": "open",
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    health_alerts[alert_id] = alert
    
    return alert


@router.get("/alerts")
async def list_health_alerts(
    account_id: Optional[str] = None,
    severity: Optional[AlertSeverity] = None,
    status: str = Query(default="open"),
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """List health alerts"""
    result = [a for a in health_alerts.values() if a.get("tenant_id") == tenant_id]
    
    if account_id:
        result = [a for a in result if a.get("account_id") == account_id]
    if severity:
        result = [a for a in result if a.get("severity") == severity.value]
    if status:
        result = [a for a in result if a.get("status") == status]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"alerts": result[:limit], "total": len(result)}


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: str = Query(default="")
):
    """Resolve a health alert"""
    if alert_id not in health_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = health_alerts[alert_id]
    alert["status"] = "resolved"
    alert["resolved_at"] = datetime.utcnow().isoformat()
    alert["resolution_notes"] = resolution_notes
    
    return alert


@router.put("/alerts/{alert_id}/snooze")
async def snooze_alert(
    alert_id: str,
    snooze_days: int = Query(default=7, ge=1, le=30)
):
    """Snooze a health alert"""
    if alert_id not in health_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = health_alerts[alert_id]
    alert["status"] = "snoozed"
    alert["snoozed_until"] = (datetime.utcnow() + timedelta(days=snooze_days)).isoformat()
    
    return alert


# Health Metrics
@router.get("/accounts/{account_id}/metrics")
async def get_account_metrics(
    account_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get detailed health metrics for an account"""
    now = datetime.utcnow()
    
    metrics = {
        "account_id": account_id,
        "period_days": days,
        "product_usage": {
            "dau": random.randint(10, 100),
            "mau": random.randint(50, 200),
            "sessions_per_user": round(random.uniform(3, 15), 1),
            "feature_adoption": round(random.uniform(0.3, 0.9), 2),
            "trend": random.choice(["up", "down", "stable"])
        },
        "support": {
            "open_tickets": random.randint(0, 10),
            "avg_resolution_hours": round(random.uniform(4, 48), 1),
            "csat_score": round(random.uniform(3.5, 5.0), 1),
            "escalations": random.randint(0, 5)
        },
        "engagement": {
            "last_login_days_ago": random.randint(0, 30),
            "email_response_rate": round(random.uniform(0.2, 0.8), 2),
            "meeting_attendance": round(random.uniform(0.5, 1.0), 2),
            "nps_score": random.randint(-20, 80)
        },
        "financial": {
            "arr": random.randint(50000, 500000),
            "payment_status": random.choice(["current", "overdue", "at_risk"]),
            "expansion_potential": round(random.uniform(0.1, 0.5), 2),
            "churn_risk": round(random.uniform(0.05, 0.30), 2)
        }
    }
    
    return metrics


@router.get("/accounts/{account_id}/timeline")
async def get_health_timeline(
    account_id: str,
    days: int = Query(default=30, ge=7, le=90)
):
    """Get health score timeline for an account"""
    now = datetime.utcnow()
    
    timeline = []
    base_score = random.randint(50, 80)
    
    for i in range(days):
        date = (now - timedelta(days=days - i)).isoformat()[:10]
        score = max(30, min(100, base_score + random.randint(-10, 10)))
        base_score = score  # Random walk
        
        timeline.append({
            "date": date,
            "score": score,
            "status": "excellent" if score >= 80 else "healthy" if score >= 60 else "at_risk" if score >= 40 else "critical"
        })
    
    return {
        "account_id": account_id,
        "timeline": timeline,
        "trend": "improving" if timeline[-1]["score"] > timeline[0]["score"] else "declining" if timeline[-1]["score"] < timeline[0]["score"] else "stable"
    }


# Playbooks
@router.get("/playbooks")
async def list_health_playbooks(tenant_id: str = Query(default="default")):
    """List health intervention playbooks"""
    default_playbooks = [
        {
            "id": "pb_low_usage",
            "name": "Low Usage Intervention",
            "trigger": "Usage drops below 50%",
            "steps": [
                "Send usage report email",
                "Schedule training session",
                "Create success plan"
            ]
        },
        {
            "id": "pb_at_risk",
            "name": "At-Risk Account Recovery",
            "trigger": "Health score drops below 50",
            "steps": [
                "Assign CSM",
                "Executive outreach",
                "Create recovery plan",
                "Weekly check-ins"
            ]
        },
        {
            "id": "pb_support_issues",
            "name": "Support Escalation Response",
            "trigger": "Multiple escalations in 30 days",
            "steps": [
                "Root cause analysis",
                "Engineering review",
                "Customer communication",
                "Resolution tracking"
            ]
        }
    ]
    
    custom = [p for p in playbooks.values() if p.get("tenant_id") == tenant_id]
    
    return {"playbooks": default_playbooks + custom}


@router.post("/accounts/{account_id}/playbook/{playbook_id}")
async def trigger_playbook(
    account_id: str,
    playbook_id: str
):
    """Trigger a health playbook for an account"""
    return {
        "account_id": account_id,
        "playbook_id": playbook_id,
        "status": "triggered",
        "triggered_at": datetime.utcnow().isoformat(),
        "assigned_to": f"csm_{random.randint(1, 5)}",
        "next_step": "Initial outreach"
    }


# Analytics
@router.get("/analytics/trends")
async def get_health_trends(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get health trends across all accounts"""
    timeline = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).isoformat()[:10]
        timeline.append({
            "date": date,
            "avg_score": random.randint(60, 80),
            "excellent_count": random.randint(5, 15),
            "at_risk_count": random.randint(2, 8),
            "critical_count": random.randint(0, 3)
        })
    
    return {
        "period_days": days,
        "timeline": timeline,
        "summary": {
            "current_avg": timeline[-1]["avg_score"],
            "previous_avg": timeline[0]["avg_score"],
            "change": timeline[-1]["avg_score"] - timeline[0]["avg_score"]
        }
    }


@router.get("/analytics/risk")
async def get_risk_analysis(tenant_id: str = Query(default="default")):
    """Get risk analysis for portfolio"""
    return {
        "total_accounts": random.randint(50, 200),
        "total_arr": random.randint(5000000, 20000000),
        "at_risk_arr": random.randint(500000, 2000000),
        "churn_forecast": {
            "next_30_days": random.randint(1, 5),
            "next_90_days": random.randint(3, 10),
            "forecast_arr_impact": random.randint(100000, 500000)
        },
        "top_risk_factors": [
            {"factor": "Low product usage", "accounts_affected": random.randint(5, 20)},
            {"factor": "Support escalations", "accounts_affected": random.randint(3, 10)},
            {"factor": "Payment issues", "accounts_affected": random.randint(2, 8)}
        ]
    }
