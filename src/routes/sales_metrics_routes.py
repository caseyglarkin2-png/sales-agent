"""
Sales Metrics Routes - Core sales KPIs and metrics tracking
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

router = APIRouter(prefix="/sales-metrics", tags=["Sales Metrics"])


class MetricCategory(str, Enum):
    REVENUE = "revenue"
    PIPELINE = "pipeline"
    ACTIVITY = "activity"
    CONVERSION = "conversion"
    EFFICIENCY = "efficiency"
    FORECAST = "forecast"


class MetricPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class AggregationType(str, Enum):
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


# In-memory storage
custom_metrics = {}
metric_goals = {}
metric_alerts = {}


class CustomMetricCreate(BaseModel):
    name: str
    category: MetricCategory
    formula: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class MetricGoalCreate(BaseModel):
    metric_name: str
    target_value: float
    period: MetricPeriod
    owner_type: str = "org"  # org, team, rep
    owner_id: Optional[str] = None


# Core Metrics Dashboard
@router.get("/dashboard")
async def get_metrics_dashboard(
    period: MetricPeriod = Query(default=MetricPeriod.MONTH),
    tenant_id: str = Query(default="default")
):
    """Get comprehensive metrics dashboard"""
    now = datetime.utcnow()
    
    # Revenue metrics
    closed_won = random.randint(500000, 2000000)
    target = random.randint(700000, 2500000)
    
    return {
        "period": period.value,
        "as_of": now.isoformat(),
        "revenue": {
            "closed_won": closed_won,
            "target": target,
            "attainment": round(closed_won / target, 3),
            "forecast": int(closed_won * random.uniform(1.1, 1.4)),
            "yoy_growth": round(random.uniform(-0.1, 0.3), 3)
        },
        "pipeline": {
            "total_value": random.randint(3000000, 10000000),
            "weighted_value": random.randint(1500000, 5000000),
            "coverage_ratio": round(random.uniform(2.5, 5.0), 2),
            "deals_count": random.randint(50, 200),
            "avg_deal_size": random.randint(20000, 100000),
            "pipeline_velocity": round(random.uniform(0.8, 1.5), 2)
        },
        "activity": {
            "total_activities": random.randint(5000, 20000),
            "calls": random.randint(1000, 5000),
            "emails": random.randint(3000, 12000),
            "meetings": random.randint(200, 1000),
            "demos": random.randint(100, 500)
        },
        "conversion": {
            "lead_to_opportunity": round(random.uniform(0.10, 0.30), 3),
            "opportunity_to_close": round(random.uniform(0.15, 0.35), 3),
            "overall_win_rate": round(random.uniform(0.18, 0.32), 3)
        },
        "efficiency": {
            "avg_cycle_time_days": random.randint(30, 90),
            "activities_per_deal": random.randint(30, 100),
            "cost_per_acquisition": random.randint(500, 5000)
        }
    }


# Individual Metrics
@router.get("/revenue")
async def get_revenue_metrics(
    period: MetricPeriod = Query(default=MetricPeriod.MONTH),
    compare_previous: bool = Query(default=True),
    tenant_id: str = Query(default="default")
):
    """Get detailed revenue metrics"""
    current = random.randint(500000, 2000000)
    previous = random.randint(400000, 1800000)
    
    return {
        "period": period.value,
        "current_period": {
            "closed_won": current,
            "new_business": int(current * random.uniform(0.5, 0.7)),
            "expansion": int(current * random.uniform(0.2, 0.35)),
            "renewal": int(current * random.uniform(0.1, 0.2)),
            "deals_won": random.randint(10, 50),
            "avg_deal_size": int(current / random.randint(10, 50)),
            "largest_deal": int(current * random.uniform(0.1, 0.3))
        },
        "previous_period": {
            "closed_won": previous,
            "deals_won": random.randint(8, 45)
        } if compare_previous else None,
        "change": {
            "value": current - previous,
            "percentage": round((current - previous) / previous, 3) if previous > 0 else 0
        } if compare_previous else None,
        "breakdown_by_segment": [
            {"segment": "Enterprise", "revenue": int(current * 0.45)},
            {"segment": "Mid-Market", "revenue": int(current * 0.35)},
            {"segment": "SMB", "revenue": int(current * 0.20)}
        ]
    }


@router.get("/pipeline")
async def get_pipeline_metrics(
    period: MetricPeriod = Query(default=MetricPeriod.MONTH),
    tenant_id: str = Query(default="default")
):
    """Get detailed pipeline metrics"""
    pipeline_value = random.randint(3000000, 10000000)
    
    return {
        "period": period.value,
        "total_pipeline": {
            "value": pipeline_value,
            "weighted": int(pipeline_value * random.uniform(0.4, 0.6)),
            "deal_count": random.randint(50, 200)
        },
        "by_stage": [
            {"stage": "Qualification", "value": int(pipeline_value * 0.25), "count": random.randint(20, 60)},
            {"stage": "Discovery", "value": int(pipeline_value * 0.25), "count": random.randint(15, 45)},
            {"stage": "Proposal", "value": int(pipeline_value * 0.20), "count": random.randint(10, 35)},
            {"stage": "Negotiation", "value": int(pipeline_value * 0.18), "count": random.randint(8, 25)},
            {"stage": "Closing", "value": int(pipeline_value * 0.12), "count": random.randint(5, 15)}
        ],
        "created_this_period": random.randint(1000000, 4000000),
        "closed_won_this_period": random.randint(500000, 2000000),
        "closed_lost_this_period": random.randint(300000, 1500000),
        "pipeline_coverage": round(random.uniform(2.5, 5.0), 2),
        "velocity": {
            "value": round(random.uniform(0.8, 1.5), 2),
            "trend": random.choice(["improving", "stable", "declining"])
        }
    }


@router.get("/conversion")
async def get_conversion_metrics(
    period: MetricPeriod = Query(default=MetricPeriod.MONTH),
    tenant_id: str = Query(default="default")
):
    """Get conversion metrics across the funnel"""
    return {
        "period": period.value,
        "funnel": {
            "leads": random.randint(1000, 5000),
            "mqls": random.randint(300, 1500),
            "sqls": random.randint(150, 800),
            "opportunities": random.randint(50, 300),
            "proposals": random.randint(30, 150),
            "closed_won": random.randint(10, 60)
        },
        "conversion_rates": {
            "lead_to_mql": round(random.uniform(0.20, 0.40), 3),
            "mql_to_sql": round(random.uniform(0.30, 0.60), 3),
            "sql_to_opportunity": round(random.uniform(0.25, 0.50), 3),
            "opportunity_to_proposal": round(random.uniform(0.50, 0.80), 3),
            "proposal_to_close": round(random.uniform(0.20, 0.50), 3),
            "overall_win_rate": round(random.uniform(0.15, 0.35), 3)
        },
        "by_source": [
            {"source": "Inbound", "win_rate": round(random.uniform(0.20, 0.40), 3)},
            {"source": "Outbound", "win_rate": round(random.uniform(0.10, 0.25), 3)},
            {"source": "Referral", "win_rate": round(random.uniform(0.30, 0.50), 3)},
            {"source": "Partner", "win_rate": round(random.uniform(0.25, 0.45), 3)}
        ],
        "avg_cycle_time_days": {
            "qualification_to_close": random.randint(30, 90),
            "by_stage": {
                "qualification": random.randint(5, 15),
                "discovery": random.randint(10, 25),
                "proposal": random.randint(10, 20),
                "negotiation": random.randint(7, 21),
                "closing": random.randint(5, 14)
            }
        }
    }


@router.get("/activity")
async def get_activity_metrics(
    period: MetricPeriod = Query(default=MetricPeriod.WEEK),
    tenant_id: str = Query(default="default")
):
    """Get activity metrics"""
    return {
        "period": period.value,
        "totals": {
            "calls": random.randint(500, 3000),
            "emails_sent": random.randint(2000, 10000),
            "meetings_scheduled": random.randint(100, 500),
            "meetings_held": random.randint(80, 400),
            "demos": random.randint(50, 250),
            "proposals_sent": random.randint(20, 100)
        },
        "averages_per_rep": {
            "calls": random.randint(30, 100),
            "emails": random.randint(100, 400),
            "meetings": random.randint(5, 25)
        },
        "outcomes": {
            "call_connect_rate": round(random.uniform(0.10, 0.25), 3),
            "email_reply_rate": round(random.uniform(0.05, 0.15), 3),
            "meeting_show_rate": round(random.uniform(0.70, 0.95), 3),
            "demo_to_opportunity": round(random.uniform(0.30, 0.60), 3)
        },
        "productivity": {
            "activities_per_won_deal": random.randint(50, 150),
            "touches_per_meeting": random.randint(5, 15)
        }
    }


# Trends
@router.get("/trends")
async def get_metric_trends(
    metric: str = Query(...),
    days: int = Query(default=30, ge=7, le=365),
    tenant_id: str = Query(default="default")
):
    """Get metric trend over time"""
    now = datetime.utcnow()
    
    timeline = []
    base_value = random.randint(10000, 100000)
    
    for i in range(days):
        date = (now - timedelta(days=days - i)).isoformat()[:10]
        # Random walk
        base_value = max(1000, base_value + random.randint(-5000, 6000))
        timeline.append({
            "date": date,
            "value": base_value
        })
    
    return {
        "metric": metric,
        "period_days": days,
        "timeline": timeline,
        "summary": {
            "start_value": timeline[0]["value"],
            "end_value": timeline[-1]["value"],
            "min": min(t["value"] for t in timeline),
            "max": max(t["value"] for t in timeline),
            "avg": round(sum(t["value"] for t in timeline) / len(timeline)),
            "trend": "up" if timeline[-1]["value"] > timeline[0]["value"] else "down"
        }
    }


# Custom Metrics
@router.post("/custom")
async def create_custom_metric(
    request: CustomMetricCreate,
    tenant_id: str = Query(default="default")
):
    """Create a custom metric"""
    metric_id = str(uuid.uuid4())
    
    metric = {
        "id": metric_id,
        "name": request.name,
        "category": request.category.value,
        "formula": request.formula,
        "unit": request.unit,
        "description": request.description,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    custom_metrics[metric_id] = metric
    
    return metric


@router.get("/custom")
async def list_custom_metrics(tenant_id: str = Query(default="default")):
    """List custom metrics"""
    result = [m for m in custom_metrics.values() if m.get("tenant_id") == tenant_id]
    return {"metrics": result, "total": len(result)}


# Goals
@router.post("/goals")
async def create_metric_goal(
    request: MetricGoalCreate,
    tenant_id: str = Query(default="default")
):
    """Create a metric goal"""
    goal_id = str(uuid.uuid4())
    
    goal = {
        "id": goal_id,
        "metric_name": request.metric_name,
        "target_value": request.target_value,
        "current_value": 0,
        "period": request.period.value,
        "owner_type": request.owner_type,
        "owner_id": request.owner_id,
        "progress": 0,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    metric_goals[goal_id] = goal
    
    return goal


@router.get("/goals")
async def list_metric_goals(
    owner_type: Optional[str] = None,
    owner_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List metric goals"""
    result = [g for g in metric_goals.values() if g.get("tenant_id") == tenant_id]
    
    if owner_type:
        result = [g for g in result if g.get("owner_type") == owner_type]
    if owner_id:
        result = [g for g in result if g.get("owner_id") == owner_id]
    
    # Update progress
    for goal in result:
        goal["current_value"] = random.randint(0, int(goal["target_value"] * 1.3))
        goal["progress"] = round(goal["current_value"] / goal["target_value"], 3)
    
    return {"goals": result, "total": len(result)}


# Comparisons
@router.get("/compare")
async def compare_metrics(
    metric: str = Query(...),
    compare_by: str = Query(default="team"),  # team, rep, period
    ids: Optional[List[str]] = Query(default=None),
    tenant_id: str = Query(default="default")
):
    """Compare metrics across dimensions"""
    comparison = []
    
    items = ids or [f"item_{i}" for i in range(5)]
    
    for item in items:
        comparison.append({
            "id": item,
            "name": f"{compare_by.title()} {item[-1]}",
            "current_value": random.randint(50000, 300000),
            "previous_value": random.randint(40000, 280000),
            "change_pct": round(random.uniform(-0.2, 0.3), 3),
            "rank": 0
        })
    
    comparison.sort(key=lambda x: x["current_value"], reverse=True)
    for i, item in enumerate(comparison):
        item["rank"] = i + 1
    
    return {
        "metric": metric,
        "compare_by": compare_by,
        "comparison": comparison
    }


# Benchmarks
@router.get("/benchmarks")
async def get_benchmarks(tenant_id: str = Query(default="default")):
    """Get industry benchmarks"""
    return {
        "industry": "B2B SaaS",
        "metrics": {
            "win_rate": {"your_value": round(random.uniform(0.20, 0.30), 3), "benchmark": 0.25, "percentile": random.randint(40, 80)},
            "avg_deal_size": {"your_value": random.randint(25000, 75000), "benchmark": 50000, "percentile": random.randint(35, 75)},
            "cycle_time_days": {"your_value": random.randint(45, 90), "benchmark": 60, "percentile": random.randint(30, 70)},
            "quota_attainment": {"your_value": round(random.uniform(0.75, 1.10), 2), "benchmark": 0.85, "percentile": random.randint(45, 85)},
            "pipeline_coverage": {"your_value": round(random.uniform(2.5, 4.5), 1), "benchmark": 3.5, "percentile": random.randint(40, 75)}
        },
        "source": "Industry Analysis 2024",
        "updated_at": datetime.utcnow().isoformat()
    }
