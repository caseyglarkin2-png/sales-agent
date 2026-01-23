"""
Customer Health Scoring Routes - Customer health metrics, usage analytics, and expansion signals
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

router = APIRouter(prefix="/customer-health", tags=["Customer Health"])


class HealthStatus(str, Enum):
    EXCELLENT = "excellent"
    HEALTHY = "healthy"
    NEEDS_ATTENTION = "needs_attention"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


class SignalType(str, Enum):
    USAGE = "usage"
    ENGAGEMENT = "engagement"
    SUPPORT = "support"
    BILLING = "billing"
    ADOPTION = "adoption"
    EXPANSION = "expansion"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# In-memory storage
health_scores = {}
health_alerts = {}
usage_data = {}


class HealthScoreUpdate(BaseModel):
    customer_id: str
    score_adjustments: Dict[str, float]
    notes: Optional[str] = None


class UsageDataCreate(BaseModel):
    customer_id: str
    metric_name: str
    value: float
    recorded_at: Optional[datetime] = None


# Health Scores
@router.get("/scores")
async def list_health_scores(
    status: Optional[HealthStatus] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    segment: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    tenant_id: str = Query(default="default")
):
    """List customer health scores"""
    # Generate mock data
    customers = []
    for i in range(20):
        score = random.randint(20, 100)
        
        if score >= 80:
            status_val = HealthStatus.EXCELLENT.value
        elif score >= 65:
            status_val = HealthStatus.HEALTHY.value
        elif score >= 50:
            status_val = HealthStatus.NEEDS_ATTENTION.value
        elif score >= 35:
            status_val = HealthStatus.AT_RISK.value
        else:
            status_val = HealthStatus.CRITICAL.value
        
        customers.append({
            "customer_id": f"cust_{1000+i}",
            "customer_name": f"Customer {i+1} Inc",
            "overall_score": score,
            "status": status_val,
            "trend": random.choice(["improving", "stable", "declining"]),
            "trend_delta": random.randint(-15, 15),
            "component_scores": {
                "usage": random.randint(30, 100),
                "engagement": random.randint(30, 100),
                "support": random.randint(40, 100),
                "adoption": random.randint(30, 100),
                "billing": random.randint(50, 100)
            },
            "last_activity": (datetime.utcnow() - timedelta(days=random.randint(0, 14))).isoformat(),
            "arr": random.randint(10000, 500000),
            "segment": random.choice(["enterprise", "mid_market", "smb"])
        })
    
    result = customers
    
    if status:
        result = [c for c in result if c.get("status") == status.value]
    if min_score is not None:
        result = [c for c in result if c.get("overall_score", 0) >= min_score]
    if max_score is not None:
        result = [c for c in result if c.get("overall_score", 100) <= max_score]
    if segment:
        result = [c for c in result if c.get("segment") == segment]
    
    return {
        "scores": result[:limit],
        "total": len(result),
        "summary": {
            "avg_score": round(sum(c["overall_score"] for c in result) / len(result), 1) if result else 0,
            "at_risk_count": len([c for c in result if c["status"] in ["at_risk", "critical"]]),
            "improving_count": len([c for c in result if c["trend"] == "improving"]),
            "declining_count": len([c for c in result if c["trend"] == "declining"])
        }
    }


@router.get("/scores/{customer_id}")
async def get_customer_health(
    customer_id: str,
    include_history: bool = True,
    tenant_id: str = Query(default="default")
):
    """Get detailed health score for a customer"""
    base_score = random.randint(45, 90)
    
    health = {
        "customer_id": customer_id,
        "customer_name": f"Customer {customer_id.split('_')[1] if '_' in customer_id else customer_id}",
        "overall_score": base_score,
        "status": HealthStatus.HEALTHY.value if base_score >= 65 else HealthStatus.AT_RISK.value,
        "last_calculated": datetime.utcnow().isoformat(),
        "component_scores": {
            "usage": {
                "score": random.randint(40, 100),
                "weight": 0.30,
                "factors": [
                    {"name": "DAU/MAU ratio", "value": round(random.uniform(0.20, 0.60), 2), "benchmark": 0.35, "status": "healthy"},
                    {"name": "Feature adoption", "value": f"{random.randint(40, 80)}%", "benchmark": "60%", "status": "needs_attention"},
                    {"name": "Last login", "value": f"{random.randint(1, 7)} days ago", "benchmark": "7 days", "status": "healthy"}
                ]
            },
            "engagement": {
                "score": random.randint(40, 100),
                "weight": 0.25,
                "factors": [
                    {"name": "Email open rate", "value": f"{random.randint(20, 50)}%", "benchmark": "30%", "status": "healthy"},
                    {"name": "Training completed", "value": f"{random.randint(2, 8)}/10 modules", "status": "needs_attention"},
                    {"name": "Exec sponsor engagement", "value": random.choice(["active", "inactive"]), "status": "at_risk"}
                ]
            },
            "support": {
                "score": random.randint(50, 100),
                "weight": 0.20,
                "factors": [
                    {"name": "Open tickets", "value": random.randint(0, 5), "benchmark": "< 3", "status": "healthy"},
                    {"name": "CSAT score", "value": round(random.uniform(3.5, 5.0), 1), "benchmark": "4.0", "status": "healthy"},
                    {"name": "Escalations (90d)", "value": random.randint(0, 2), "status": "healthy"}
                ]
            },
            "adoption": {
                "score": random.randint(30, 100),
                "weight": 0.15,
                "factors": [
                    {"name": "Licensed users active", "value": f"{random.randint(50, 95)}%", "benchmark": "70%", "status": "healthy"},
                    {"name": "Core features used", "value": f"{random.randint(4, 10)}/12", "status": "needs_attention"},
                    {"name": "Integration depth", "value": random.choice(["low", "medium", "high"]), "status": "medium"}
                ]
            },
            "billing": {
                "score": random.randint(60, 100),
                "weight": 0.10,
                "factors": [
                    {"name": "Payment status", "value": random.choice(["current", "current", "overdue"]), "status": "healthy"},
                    {"name": "Invoice disputes", "value": random.randint(0, 1), "status": "healthy"},
                    {"name": "Contract status", "value": f"{random.randint(30, 300)} days to renewal", "status": "healthy"}
                ]
            }
        },
        "risk_factors": [],
        "expansion_signals": []
    }
    
    # Add risk factors for lower scores
    if base_score < 70:
        health["risk_factors"] = [
            {
                "signal": "Usage decline",
                "severity": AlertSeverity.MEDIUM.value,
                "description": "Weekly active users down 25% vs last month",
                "recommended_action": "Schedule usage review with customer"
            },
            {
                "signal": "Champion departed",
                "severity": AlertSeverity.HIGH.value,
                "description": "Primary contact left the company 2 weeks ago",
                "recommended_action": "Identify new champion urgently"
            }
        ]
    
    # Add expansion signals for higher scores
    if base_score >= 70:
        health["expansion_signals"] = [
            {
                "signal": "Usage exceeding quota",
                "strength": "strong",
                "description": "At 120% of licensed capacity",
                "opportunity": "Upsell additional seats"
            },
            {
                "signal": "Feature interest",
                "strength": "medium",
                "description": "Multiple requests for Enterprise features",
                "opportunity": "Upgrade to Enterprise tier"
            }
        ]
    
    if include_history:
        health["score_history"] = [
            {
                "date": (datetime.utcnow() - timedelta(days=i*7)).strftime("%Y-%m-%d"),
                "score": max(20, min(100, base_score + random.randint(-10, 10)))
            }
            for i in range(12, -1, -1)
        ]
    
    return health


@router.post("/scores/{customer_id}/recalculate")
async def recalculate_health_score(
    customer_id: str,
    tenant_id: str = Query(default="default")
):
    """Trigger recalculation of customer health score"""
    new_score = random.randint(40, 95)
    
    return {
        "customer_id": customer_id,
        "previous_score": random.randint(40, 95),
        "new_score": new_score,
        "change": random.randint(-10, 10),
        "recalculated_at": datetime.utcnow().isoformat()
    }


# Alerts
@router.get("/alerts")
async def list_health_alerts(
    severity: Optional[AlertSeverity] = None,
    signal_type: Optional[SignalType] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    tenant_id: str = Query(default="default")
):
    """List health alerts"""
    alerts = []
    for i in range(15):
        alerts.append({
            "id": f"alert_{i+1}",
            "customer_id": f"cust_{1000+i}",
            "customer_name": f"Customer {i+1} Inc",
            "signal_type": random.choice([s.value for s in SignalType]),
            "severity": random.choice([s.value for s in AlertSeverity]),
            "title": random.choice([
                "Usage drop detected",
                "Support tickets increasing",
                "No login in 14 days",
                "Billing overdue",
                "Champion left company",
                "Negative NPS response"
            ]),
            "description": "Alert details...",
            "created_at": (datetime.utcnow() - timedelta(hours=random.randint(1, 168))).isoformat(),
            "acknowledged": random.choice([True, False, False]),
            "acknowledged_by": None,
            "recommended_action": random.choice([
                "Schedule check-in call",
                "Escalate to CSM manager",
                "Send re-engagement email",
                "Review account health"
            ])
        })
    
    result = alerts
    
    if severity:
        result = [a for a in result if a["severity"] == severity.value]
    if signal_type:
        result = [a for a in result if a["signal_type"] == signal_type.value]
    if acknowledged is not None:
        result = [a for a in result if a["acknowledged"] == acknowledged]
    
    return {"alerts": result[:limit], "total": len(result)}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user_email: str,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Acknowledge a health alert"""
    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_by": user_email,
        "acknowledged_at": datetime.utcnow().isoformat(),
        "notes": notes
    }


# Usage Analytics
@router.get("/usage/{customer_id}")
async def get_customer_usage(
    customer_id: str,
    period: str = Query(default="30d"),
    tenant_id: str = Query(default="default")
):
    """Get usage analytics for a customer"""
    days = int(period.replace("d", "")) if "d" in period else 30
    
    return {
        "customer_id": customer_id,
        "period": period,
        "summary": {
            "dau": random.randint(20, 200),
            "mau": random.randint(50, 500),
            "dau_mau_ratio": round(random.uniform(0.20, 0.60), 2),
            "total_sessions": random.randint(500, 5000),
            "avg_session_duration": f"{random.randint(5, 25)} min",
            "active_users_pct": round(random.uniform(0.50, 0.95), 2)
        },
        "feature_usage": [
            {"feature": "Dashboard", "usage_pct": random.randint(70, 100), "trend": random.choice(["up", "stable", "down"])},
            {"feature": "Reports", "usage_pct": random.randint(40, 80), "trend": random.choice(["up", "stable", "down"])},
            {"feature": "Automation", "usage_pct": random.randint(20, 60), "trend": random.choice(["up", "stable", "down"])},
            {"feature": "Integrations", "usage_pct": random.randint(30, 70), "trend": random.choice(["up", "stable", "down"])},
            {"feature": "API", "usage_pct": random.randint(10, 50), "trend": random.choice(["up", "stable", "down"])}
        ],
        "usage_trend": [
            {
                "date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "active_users": random.randint(30, 150),
                "sessions": random.randint(50, 300)
            }
            for i in range(days-1, -1, -1)
        ][:30]  # Limit to 30 data points
    }


@router.get("/usage/compare")
async def compare_usage(
    customer_ids: str = Query(..., description="Comma-separated customer IDs"),
    metric: str = Query(default="dau"),
    tenant_id: str = Query(default="default")
):
    """Compare usage across customers"""
    ids = customer_ids.split(",")
    
    return {
        "metric": metric,
        "comparison": [
            {
                "customer_id": cid,
                "value": random.randint(20, 200),
                "benchmark": random.randint(50, 150),
                "percentile": random.randint(30, 95)
            }
            for cid in ids
        ]
    }


# Expansion Signals
@router.get("/expansion-signals")
async def list_expansion_signals(
    strength: Optional[str] = None,
    signal_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    tenant_id: str = Query(default="default")
):
    """List expansion signals across customers"""
    signals = []
    signal_types = ["usage_growth", "feature_request", "user_growth", "usage_ceiling", "competitive_mention"]
    
    for i in range(20):
        signals.append({
            "id": f"signal_{i+1}",
            "customer_id": f"cust_{1000+i}",
            "customer_name": f"Customer {i+1} Inc",
            "signal_type": random.choice(signal_types),
            "strength": random.choice(["strong", "medium", "weak"]),
            "description": random.choice([
                "Usage at 95% of licensed capacity",
                "Requested enterprise SSO feature",
                "Added 20 new users this month",
                "Hitting API rate limits frequently",
                "Asked about additional product lines"
            ]),
            "estimated_opportunity": random.randint(5000, 100000),
            "recommended_action": "Schedule expansion discussion",
            "detected_at": (datetime.utcnow() - timedelta(days=random.randint(0, 14))).isoformat(),
            "current_arr": random.randint(20000, 200000)
        })
    
    result = signals
    
    if strength:
        result = [s for s in result if s["strength"] == strength]
    
    return {
        "signals": result[:limit],
        "total": len(result),
        "total_opportunity": sum(s["estimated_opportunity"] for s in result)
    }


# Analytics Dashboard
@router.get("/analytics")
async def get_health_analytics(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get customer health analytics summary"""
    return {
        "period": period,
        "generated_at": datetime.utcnow().isoformat(),
        "portfolio_health": {
            "avg_score": random.randint(60, 80),
            "median_score": random.randint(60, 80),
            "distribution": {
                "excellent": random.randint(15, 30),
                "healthy": random.randint(30, 45),
                "needs_attention": random.randint(15, 25),
                "at_risk": random.randint(5, 15),
                "critical": random.randint(2, 8)
            }
        },
        "trends": {
            "avg_score_change": round(random.uniform(-5, 5), 1),
            "customers_improved": random.randint(30, 60),
            "customers_declined": random.randint(10, 30),
            "customers_stable": random.randint(20, 40)
        },
        "at_risk_revenue": random.randint(500000, 2000000),
        "expansion_pipeline": random.randint(200000, 800000),
        "top_risk_factors": [
            {"factor": "Usage decline", "affected_customers": random.randint(10, 30)},
            {"factor": "No champion identified", "affected_customers": random.randint(5, 20)},
            {"factor": "Overdue renewal", "affected_customers": random.randint(5, 15)}
        ],
        "action_recommendations": [
            {"action": "Schedule QBRs for at-risk accounts", "priority": "high", "affected_customers": random.randint(8, 15)},
            {"action": "Send re-engagement campaign", "priority": "medium", "affected_customers": random.randint(15, 30)},
            {"action": "Pursue expansion opportunities", "priority": "medium", "affected_customers": random.randint(20, 40)}
        ]
    }
