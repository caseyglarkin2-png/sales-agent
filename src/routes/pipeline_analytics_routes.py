"""
Pipeline Analytics V2 Routes - Advanced pipeline analysis and insights
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

router = APIRouter(prefix="/pipeline-analytics", tags=["Pipeline Analytics V2"])


class PipelineView(str, Enum):
    STAGE = "stage"
    REP = "rep"
    TEAM = "team"
    TERRITORY = "territory"
    SEGMENT = "segment"
    PRODUCT = "product"
    SOURCE = "source"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PipelineStage(str, Enum):
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"


# In-memory storage
pipeline_snapshots = {}
pipeline_alerts = {}
pipeline_goals = {}


@router.get("/overview")
async def get_pipeline_overview(
    view: PipelineView = PipelineView.STAGE,
    period: str = Query(default="current_quarter"),
    tenant_id: str = Query(default="default")
):
    """Get pipeline overview"""
    total_pipeline = random.uniform(2000000, 10000000)
    weighted_pipeline = total_pipeline * random.uniform(0.3, 0.5)
    
    # Generate breakdown based on view
    breakdown = []
    if view == PipelineView.STAGE:
        stages = ["Qualification", "Discovery", "Proposal", "Negotiation", "Closing"]
        remaining = total_pipeline
        for i, stage in enumerate(stages):
            amount = remaining * random.uniform(0.15, 0.4) if i < len(stages) - 1 else remaining
            remaining -= amount
            breakdown.append({
                "name": stage,
                "amount": round(amount, 2),
                "deal_count": random.randint(5, 30),
                "weighted_amount": round(amount * (0.1 + i * 0.2), 2),
                "avg_age_days": random.randint(5, 45)
            })
    elif view == PipelineView.REP:
        for i in range(random.randint(5, 10)):
            amount = random.uniform(200000, 800000)
            breakdown.append({
                "name": f"Rep {i+1}",
                "rep_id": str(uuid.uuid4()),
                "amount": round(amount, 2),
                "deal_count": random.randint(5, 20),
                "weighted_amount": round(amount * random.uniform(0.3, 0.6), 2),
                "quota_attainment": round(random.uniform(0.5, 1.5), 2)
            })
    
    return {
        "total_pipeline": round(total_pipeline, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        "deal_count": random.randint(50, 200),
        "avg_deal_size": round(total_pipeline / random.randint(50, 200), 2),
        "view": view.value,
        "period": period,
        "breakdown": breakdown,
        "trend": {
            "direction": random.choice([d.value for d in TrendDirection]),
            "change_pct": round(random.uniform(-15, 25), 2)
        }
    }


@router.get("/velocity")
async def get_pipeline_velocity(
    period: str = Query(default="last_90_days"),
    segment: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get pipeline velocity metrics"""
    stages = ["Qualification", "Discovery", "Proposal", "Negotiation", "Closing"]
    
    stage_metrics = []
    cumulative_days = 0
    
    for stage in stages:
        avg_days = random.uniform(5, 20)
        cumulative_days += avg_days
        
        stage_metrics.append({
            "stage": stage,
            "avg_days": round(avg_days, 1),
            "median_days": round(avg_days * random.uniform(0.8, 1.1), 1),
            "conversion_rate": round(random.uniform(0.4, 0.9), 3),
            "deals_in_stage": random.randint(10, 50)
        })
    
    return {
        "total_cycle_days": round(cumulative_days, 1),
        "median_cycle_days": round(cumulative_days * 0.85, 1),
        "stage_metrics": stage_metrics,
        "velocity_trend": {
            "current": round(cumulative_days, 1),
            "previous": round(cumulative_days * random.uniform(0.9, 1.2), 1),
            "change_pct": round(random.uniform(-15, 15), 2)
        },
        "bottlenecks": [
            {"stage": random.choice(stages), "impact": "high", "recommendation": "Increase follow-up frequency"}
        ]
    }


@router.get("/conversion")
async def get_conversion_analysis(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get conversion funnel analysis"""
    funnel = [
        {"stage": "Lead", "count": random.randint(500, 1000), "value": random.uniform(5000000, 10000000)},
        {"stage": "MQL", "count": random.randint(200, 500), "value": random.uniform(3000000, 7000000)},
        {"stage": "SQL", "count": random.randint(100, 300), "value": random.uniform(2000000, 5000000)},
        {"stage": "Opportunity", "count": random.randint(50, 150), "value": random.uniform(1500000, 4000000)},
        {"stage": "Proposal", "count": random.randint(30, 100), "value": random.uniform(1000000, 3000000)},
        {"stage": "Closed Won", "count": random.randint(10, 50), "value": random.uniform(500000, 2000000)}
    ]
    
    # Calculate conversion rates
    for i in range(1, len(funnel)):
        funnel[i]["conversion_rate"] = round(funnel[i]["count"] / funnel[i-1]["count"], 3)
        funnel[i]["value_conversion"] = round(funnel[i]["value"] / funnel[i-1]["value"], 3)
    
    funnel[0]["conversion_rate"] = 1.0
    funnel[0]["value_conversion"] = 1.0
    
    return {
        "funnel": funnel,
        "overall_conversion": round(funnel[-1]["count"] / funnel[0]["count"], 4),
        "overall_value_conversion": round(funnel[-1]["value"] / funnel[0]["value"], 4),
        "best_performing_stage": random.choice(["MQL", "SQL", "Opportunity"]),
        "needs_improvement": random.choice(["Proposal", "Negotiation"])
    }


@router.get("/aging")
async def get_pipeline_aging(
    threshold_days: int = Query(default=30),
    tenant_id: str = Query(default="default")
):
    """Get pipeline aging analysis"""
    aging_buckets = [
        {"bucket": "0-15 days", "deal_count": random.randint(20, 50), "value": random.uniform(500000, 1500000)},
        {"bucket": "16-30 days", "deal_count": random.randint(15, 40), "value": random.uniform(400000, 1200000)},
        {"bucket": "31-60 days", "deal_count": random.randint(10, 30), "value": random.uniform(300000, 1000000)},
        {"bucket": "61-90 days", "deal_count": random.randint(5, 20), "value": random.uniform(200000, 800000)},
        {"bucket": "90+ days", "deal_count": random.randint(5, 15), "value": random.uniform(100000, 500000)}
    ]
    
    stale_deals = []
    for i in range(random.randint(5, 15)):
        stale_deals.append({
            "deal_id": str(uuid.uuid4()),
            "name": f"Stale Deal {i+1}",
            "amount": round(random.uniform(20000, 200000), 2),
            "age_days": random.randint(threshold_days, 120),
            "stage": random.choice(["Discovery", "Proposal", "Negotiation"]),
            "last_activity_days": random.randint(10, 60),
            "risk_level": random.choice([r.value for r in RiskLevel])
        })
    
    return {
        "aging_buckets": aging_buckets,
        "stale_deals": stale_deals,
        "total_stale_value": sum(d["value"] for d in aging_buckets[2:]),
        "stale_deal_count": sum(d["deal_count"] for d in aging_buckets[2:]),
        "recommendations": [
            "Review deals older than 60 days",
            "Set up automated follow-up reminders",
            "Consider moving stale deals to nurture sequence"
        ]
    }


@router.get("/risk-analysis")
async def get_risk_analysis(tenant_id: str = Query(default="default")):
    """Get pipeline risk analysis"""
    at_risk_deals = []
    
    for i in range(random.randint(5, 15)):
        at_risk_deals.append({
            "deal_id": str(uuid.uuid4()),
            "name": f"At-Risk Deal {i+1}",
            "amount": round(random.uniform(30000, 300000), 2),
            "stage": random.choice(["Discovery", "Proposal", "Negotiation"]),
            "risk_level": random.choice([r.value for r in RiskLevel]),
            "risk_factors": random.sample([
                "No activity in 14+ days",
                "Champion left company",
                "Budget concerns raised",
                "Competitor mentioned",
                "Close date pushed multiple times",
                "Key stakeholder unresponsive",
                "Longer than average cycle time"
            ], k=random.randint(1, 3)),
            "recommended_actions": [
                "Schedule executive alignment call",
                "Send case study relevant to their industry"
            ]
        })
    
    total_at_risk = sum(d["amount"] for d in at_risk_deals)
    
    return {
        "at_risk_deals": at_risk_deals,
        "total_at_risk_value": round(total_at_risk, 2),
        "at_risk_count": len(at_risk_deals),
        "risk_distribution": {
            "low": random.randint(20, 40),
            "medium": random.randint(10, 25),
            "high": random.randint(5, 15),
            "critical": random.randint(2, 8)
        },
        "top_risk_factors": [
            {"factor": "No recent activity", "deal_count": random.randint(5, 15)},
            {"factor": "Competitor mentioned", "deal_count": random.randint(3, 10)},
            {"factor": "Close date slipped", "deal_count": random.randint(4, 12)}
        ]
    }


@router.get("/trends")
async def get_pipeline_trends(
    days: int = Query(default=90, ge=30, le=365),
    tenant_id: str = Query(default="default")
):
    """Get pipeline trends over time"""
    trends = []
    base_value = random.uniform(3000000, 8000000)
    
    for i in range(days // 7):  # Weekly data points
        date = (datetime.utcnow() - timedelta(days=days - i * 7)).isoformat()[:10]
        variation = random.uniform(-0.1, 0.15) * i / (days // 7)
        
        trends.append({
            "date": date,
            "pipeline_value": round(base_value * (1 + variation), 2),
            "weighted_value": round(base_value * (1 + variation) * 0.4, 2),
            "deal_count": random.randint(40, 80),
            "new_deals": random.randint(5, 20),
            "closed_won": random.randint(2, 10),
            "closed_lost": random.randint(1, 5)
        })
    
    return {
        "trends": trends,
        "period_days": days,
        "summary": {
            "pipeline_growth": round(random.uniform(-10, 30), 2),
            "deal_count_change": random.randint(-20, 50),
            "avg_deal_size_change": round(random.uniform(-15, 25), 2)
        }
    }


@router.get("/sources")
async def get_pipeline_by_source(tenant_id: str = Query(default="default")):
    """Get pipeline analysis by lead source"""
    sources = [
        "Inbound - Website",
        "Inbound - Content",
        "Outbound - SDR",
        "Referral",
        "Partner",
        "Event",
        "Paid Ads"
    ]
    
    source_analysis = []
    for source in sources:
        pipeline = random.uniform(200000, 1500000)
        win_rate = random.uniform(0.15, 0.45)
        
        source_analysis.append({
            "source": source,
            "pipeline_value": round(pipeline, 2),
            "deal_count": random.randint(5, 40),
            "avg_deal_size": round(pipeline / random.randint(5, 40), 2),
            "win_rate": round(win_rate, 3),
            "avg_cycle_days": random.randint(20, 90),
            "roi": round(random.uniform(2, 15), 2) if "Paid" not in source else round(random.uniform(1.5, 5), 2)
        })
    
    source_analysis.sort(key=lambda x: x["pipeline_value"], reverse=True)
    
    return {
        "sources": source_analysis,
        "total_pipeline": sum(s["pipeline_value"] for s in source_analysis),
        "best_performing": source_analysis[0]["source"],
        "highest_win_rate": max(source_analysis, key=lambda x: x["win_rate"])["source"]
    }


@router.get("/snapshots")
async def list_pipeline_snapshots(
    limit: int = Query(default=10, le=50),
    tenant_id: str = Query(default="default")
):
    """List pipeline snapshots"""
    snapshots = [s for s in pipeline_snapshots.values() if s.get("tenant_id") == tenant_id]
    snapshots.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"snapshots": snapshots[:limit], "total": len(snapshots)}


@router.post("/snapshots")
async def create_pipeline_snapshot(
    name: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a pipeline snapshot"""
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    snapshot = {
        "id": snapshot_id,
        "name": name or f"Snapshot {now.isoformat()[:10]}",
        "pipeline_value": round(random.uniform(3000000, 10000000), 2),
        "weighted_value": round(random.uniform(1000000, 4000000), 2),
        "deal_count": random.randint(50, 150),
        "by_stage": {
            stage.value: {
                "value": round(random.uniform(200000, 1000000), 2),
                "count": random.randint(5, 30)
            }
            for stage in PipelineStage
        },
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    pipeline_snapshots[snapshot_id] = snapshot
    
    return snapshot


@router.get("/compare")
async def compare_pipeline_periods(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    tenant_id: str = Query(default="default")
):
    """Compare pipeline between two periods"""
    period1_value = random.uniform(3000000, 8000000)
    period2_value = period1_value * random.uniform(0.8, 1.3)
    
    return {
        "period1": {
            "start": period1_start,
            "end": period1_end,
            "pipeline_value": round(period1_value, 2),
            "deal_count": random.randint(40, 100),
            "avg_deal_size": round(period1_value / random.randint(40, 100), 2)
        },
        "period2": {
            "start": period2_start,
            "end": period2_end,
            "pipeline_value": round(period2_value, 2),
            "deal_count": random.randint(40, 100),
            "avg_deal_size": round(period2_value / random.randint(40, 100), 2)
        },
        "comparison": {
            "pipeline_change": round(period2_value - period1_value, 2),
            "pipeline_change_pct": round((period2_value - period1_value) / period1_value * 100, 2),
            "trending": "up" if period2_value > period1_value else "down"
        }
    }


@router.get("/goals")
async def get_pipeline_goals(tenant_id: str = Query(default="default")):
    """Get pipeline goals and progress"""
    goals = [g for g in pipeline_goals.values() if g.get("tenant_id") == tenant_id]
    
    if not goals:
        # Return default goals
        goals = [
            {
                "metric": "pipeline_value",
                "target": 10000000,
                "current": random.uniform(5000000, 12000000),
                "period": "quarterly"
            },
            {
                "metric": "new_opportunities",
                "target": 50,
                "current": random.randint(20, 60),
                "period": "monthly"
            },
            {
                "metric": "win_rate",
                "target": 0.30,
                "current": round(random.uniform(0.2, 0.4), 3),
                "period": "quarterly"
            }
        ]
    
    for goal in goals:
        goal["progress_pct"] = round(goal["current"] / goal["target"] * 100, 1)
        goal["on_track"] = goal["current"] >= goal["target"] * 0.8
    
    return {"goals": goals}
