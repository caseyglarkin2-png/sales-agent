"""
Revenue Intelligence Routes - Revenue analytics, pipeline intelligence, and deal insights
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

router = APIRouter(prefix="/revenue-intelligence", tags=["Revenue Intelligence"])


class TimeRange(str, Enum):
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    THIS_QUARTER = "this_quarter"
    THIS_YEAR = "this_year"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    CUSTOM = "custom"


class DealHealth(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    STALLED = "stalled"


class ForecastCategory(str, Enum):
    COMMIT = "commit"
    BEST_CASE = "best_case"
    PIPELINE = "pipeline"
    OMITTED = "omitted"


class AlertType(str, Enum):
    DEAL_AT_RISK = "deal_at_risk"
    PIPELINE_GAP = "pipeline_gap"
    FORECAST_CHANGE = "forecast_change"
    ACTIVITY_DROP = "activity_drop"
    ENGAGEMENT_LOW = "engagement_low"
    CLOSE_DATE_PUSHED = "close_date_pushed"


class ForecastOverride(BaseModel):
    deal_id: str
    new_amount: Optional[float] = None
    new_category: Optional[ForecastCategory] = None
    new_close_date: Optional[str] = None
    reason: Optional[str] = None


class AlertConfig(BaseModel):
    alert_type: AlertType
    enabled: bool = True
    threshold: Optional[float] = None
    notify_via: List[str] = ["email", "in_app"]


# In-memory storage
deal_signals = {}
pipeline_snapshots = {}
revenue_alerts = {}
forecast_overrides = {}


# Pipeline Intelligence
@router.get("/pipeline/overview")
async def get_pipeline_overview(
    time_range: TimeRange = TimeRange.THIS_QUARTER,
    team_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get pipeline overview with key metrics"""
    # Generate realistic mock data
    return {
        "time_range": time_range.value,
        "total_pipeline": 4250000,
        "weighted_pipeline": 2125000,
        "deals_count": 85,
        "average_deal_size": 50000,
        "win_rate": 0.32,
        "sales_cycle_days": 45,
        "by_stage": [
            {"stage": "Discovery", "count": 25, "value": 750000, "weighted": 75000},
            {"stage": "Qualification", "count": 20, "value": 1000000, "weighted": 200000},
            {"stage": "Proposal", "count": 18, "value": 900000, "weighted": 360000},
            {"stage": "Negotiation", "count": 15, "value": 1100000, "weighted": 770000},
            {"stage": "Closing", "count": 7, "value": 500000, "weighted": 400000}
        ],
        "by_source": {
            "inbound": {"count": 35, "value": 1500000},
            "outbound": {"count": 30, "value": 1750000},
            "partner": {"count": 12, "value": 650000},
            "referral": {"count": 8, "value": 350000}
        },
        "pipeline_created": 1850000,
        "pipeline_closed_won": 850000,
        "pipeline_closed_lost": 450000,
        "pipeline_slipped": 280000,
        "coverage_ratio": 3.2,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/pipeline/trends")
async def get_pipeline_trends(
    time_range: TimeRange = TimeRange.LAST_90_DAYS,
    granularity: str = Query(default="week", regex="^(day|week|month)$"),
    tenant_id: str = Query(default="default")
):
    """Get pipeline trends over time"""
    # Generate trend data
    trend_data = []
    for i in range(12):
        trend_data.append({
            "period": f"Week {i+1}",
            "pipeline_value": 4000000 + random.randint(-500000, 500000),
            "deals_created": 15 + random.randint(-5, 10),
            "deals_won": 5 + random.randint(-2, 4),
            "deals_lost": 3 + random.randint(-1, 3),
            "average_deal_size": 45000 + random.randint(-5000, 10000)
        })
    
    return {
        "time_range": time_range.value,
        "granularity": granularity,
        "trends": trend_data,
        "summary": {
            "pipeline_growth": 12.5,
            "win_rate_change": 2.3,
            "deal_velocity_change": -5.1
        }
    }


@router.get("/pipeline/velocity")
async def get_pipeline_velocity(
    time_range: TimeRange = TimeRange.THIS_QUARTER,
    segment_by: str = Query(default="stage", regex="^(stage|rep|source|product)$"),
    tenant_id: str = Query(default="default")
):
    """Get pipeline velocity metrics"""
    return {
        "time_range": time_range.value,
        "overall_velocity": {
            "avg_days_in_pipeline": 42,
            "conversion_rate": 0.28,
            "avg_deal_value": 52000
        },
        "by_stage": [
            {"stage": "Discovery", "avg_days": 8, "conversion_to_next": 0.75},
            {"stage": "Qualification", "avg_days": 12, "conversion_to_next": 0.65},
            {"stage": "Proposal", "avg_days": 10, "conversion_to_next": 0.55},
            {"stage": "Negotiation", "avg_days": 8, "conversion_to_next": 0.70},
            {"stage": "Closing", "avg_days": 4, "conversion_to_next": 0.85}
        ],
        "bottlenecks": [
            {"stage": "Qualification", "impact": "high", "suggestion": "Consider additional discovery questions"},
            {"stage": "Proposal", "impact": "medium", "suggestion": "Streamline proposal process"}
        ],
        "velocity_index": 78  # 0-100 score
    }


# Deal Intelligence
@router.get("/deals/{deal_id}/health")
async def get_deal_health(deal_id: str):
    """Get comprehensive deal health analysis"""
    # Generate mock health analysis
    health_score = random.randint(45, 95)
    
    if health_score >= 75:
        status = DealHealth.HEALTHY
    elif health_score >= 50:
        status = DealHealth.AT_RISK
    elif health_score >= 30:
        status = DealHealth.CRITICAL
    else:
        status = DealHealth.STALLED
    
    return {
        "deal_id": deal_id,
        "health_score": health_score,
        "status": status.value,
        "factors": {
            "engagement": {
                "score": random.randint(50, 100),
                "recent_activity": "Meeting scheduled for next week",
                "days_since_contact": random.randint(1, 14)
            },
            "stakeholder_coverage": {
                "score": random.randint(40, 100),
                "contacts_engaged": random.randint(2, 6),
                "decision_maker_engaged": random.choice([True, False]),
                "champion_identified": random.choice([True, False])
            },
            "deal_progression": {
                "score": random.randint(50, 100),
                "stage_duration_vs_avg": random.uniform(-0.3, 0.5),
                "on_track_for_close": random.choice([True, False])
            },
            "competitor_threat": {
                "score": random.randint(50, 100),
                "competitors_mentioned": random.randint(0, 3),
                "threat_level": random.choice(["low", "medium", "high"])
            },
            "buyer_sentiment": {
                "score": random.randint(50, 100),
                "recent_sentiment": random.choice(["positive", "neutral", "negative"]),
                "trend": random.choice(["improving", "stable", "declining"])
            }
        },
        "risks": [
            {"risk": "No executive sponsor identified", "severity": "high", "recommendation": "Schedule executive alignment meeting"},
            {"risk": "Competitor evaluation in progress", "severity": "medium", "recommendation": "Provide competitive differentiation materials"}
        ],
        "recommendations": [
            "Schedule a call with the economic buyer",
            "Send ROI calculator to quantify value",
            "Share relevant case study from similar industry"
        ],
        "similar_won_deals": [
            {"deal_id": "deal_123", "similarity": 0.85, "pattern": "Similar industry, deal size, and sales cycle"},
            {"deal_id": "deal_456", "similarity": 0.72, "pattern": "Same competitor situation"}
        ],
        "analyzed_at": datetime.utcnow().isoformat()
    }


@router.get("/deals/{deal_id}/signals")
async def get_deal_signals(deal_id: str):
    """Get buying signals and engagement indicators for a deal"""
    return {
        "deal_id": deal_id,
        "signals": [
            {
                "type": "positive",
                "signal": "Budget confirmed",
                "timestamp": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "source": "email",
                "impact": "high"
            },
            {
                "type": "positive",
                "signal": "Multiple stakeholders engaged in demos",
                "timestamp": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                "source": "meeting",
                "impact": "high"
            },
            {
                "type": "negative",
                "signal": "Requested additional competitor info",
                "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "source": "email",
                "impact": "medium"
            },
            {
                "type": "positive",
                "signal": "Asked about implementation timeline",
                "timestamp": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "source": "call",
                "impact": "high"
            }
        ],
        "engagement_timeline": [
            {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"), "score": random.randint(30, 100)}
            for i in range(30, -1, -1)
        ],
        "signal_strength": "strong",
        "buy_probability": 0.72
    }


@router.post("/deals/{deal_id}/signals")
async def add_deal_signal(
    deal_id: str,
    signal_type: str,
    description: str,
    source: Optional[str] = None,
    impact: str = "medium"
):
    """Manually add a deal signal"""
    signal_id = str(uuid.uuid4())
    
    signal = {
        "id": signal_id,
        "deal_id": deal_id,
        "type": signal_type,
        "signal": description,
        "source": source,
        "impact": impact,
        "timestamp": datetime.utcnow().isoformat(),
        "added_by": "manual"
    }
    
    if deal_id not in deal_signals:
        deal_signals[deal_id] = []
    deal_signals[deal_id].append(signal)
    
    return signal


# Forecasting
@router.get("/forecast")
async def get_forecast(
    period: str = Query(default="quarter", regex="^(month|quarter|year)$"),
    team_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get revenue forecast with AI predictions"""
    return {
        "period": period,
        "target": 5000000,
        "forecast": {
            "commit": 1850000,
            "best_case": 2450000,
            "pipeline": 4250000,
            "ai_predicted": 2150000
        },
        "attainment": {
            "closed": 850000,
            "percent_of_target": 17.0,
            "percent_of_forecast": 39.5
        },
        "gap_analysis": {
            "commit_gap": 3150000,
            "coverage_gap": 750000,
            "recommendation": "Need additional $750K in qualified pipeline to hit target"
        },
        "by_rep": [
            {"rep": "Alice Johnson", "target": 1000000, "commit": 420000, "best_case": 580000, "closed": 180000},
            {"rep": "Bob Smith", "target": 1000000, "commit": 380000, "best_case": 520000, "closed": 220000},
            {"rep": "Carol Davis", "target": 1000000, "commit": 450000, "best_case": 610000, "closed": 195000},
            {"rep": "Dan Wilson", "target": 1000000, "commit": 320000, "best_case": 420000, "closed": 155000},
            {"rep": "Eve Brown", "target": 1000000, "commit": 280000, "best_case": 320000, "closed": 100000}
        ],
        "forecast_confidence": 0.78,
        "last_updated": datetime.utcnow().isoformat()
    }


@router.post("/forecast/override")
async def override_forecast(
    request: ForecastOverride,
    user_id: str = Query(default="default")
):
    """Override AI forecast for a deal"""
    override_id = str(uuid.uuid4())
    
    override = {
        "id": override_id,
        "deal_id": request.deal_id,
        "new_amount": request.new_amount,
        "new_category": request.new_category.value if request.new_category else None,
        "new_close_date": request.new_close_date,
        "reason": request.reason,
        "overridden_by": user_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    forecast_overrides[request.deal_id] = override
    
    logger.info("forecast_overridden", deal_id=request.deal_id, user_id=user_id)
    return override


@router.get("/forecast/accuracy")
async def get_forecast_accuracy(
    periods: int = Query(default=4, ge=1, le=12),
    tenant_id: str = Query(default="default")
):
    """Get historical forecast accuracy"""
    accuracy_data = []
    for i in range(periods):
        month = (datetime.utcnow() - timedelta(days=30 * (i + 1))).strftime("%Y-%m")
        forecast = random.randint(800000, 1200000)
        actual = random.randint(750000, 1250000)
        accuracy_data.append({
            "period": month,
            "forecast": forecast,
            "actual": actual,
            "variance": actual - forecast,
            "accuracy_percent": round(min(forecast, actual) / max(forecast, actual) * 100, 1)
        })
    
    accuracy_data.reverse()
    avg_accuracy = sum(d["accuracy_percent"] for d in accuracy_data) / len(accuracy_data)
    
    return {
        "periods_analyzed": periods,
        "historical_accuracy": accuracy_data,
        "average_accuracy": round(avg_accuracy, 1),
        "trend": "improving" if accuracy_data[-1]["accuracy_percent"] > accuracy_data[0]["accuracy_percent"] else "declining"
    }


# Alerts
@router.get("/alerts")
async def get_revenue_alerts(
    alert_type: Optional[AlertType] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get revenue intelligence alerts"""
    # Generate mock alerts
    mock_alerts = [
        {
            "id": str(uuid.uuid4()),
            "type": AlertType.DEAL_AT_RISK.value,
            "severity": "high",
            "title": "Deal at risk: Acme Corp - Enterprise Deal",
            "description": "No engagement in 14 days, competitor mentioned in last call",
            "deal_id": "deal_123",
            "recommended_action": "Schedule check-in call",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "type": AlertType.PIPELINE_GAP.value,
            "severity": "high",
            "title": "Pipeline gap detected for Q4",
            "description": "Current pipeline coverage at 2.5x, below recommended 3x",
            "recommended_action": "Increase outbound activity",
            "created_at": (datetime.utcnow() - timedelta(hours=5)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "type": AlertType.CLOSE_DATE_PUSHED.value,
            "severity": "medium",
            "title": "Close date pushed: TechStart deal",
            "description": "Close date moved from Dec 15 to Jan 10",
            "deal_id": "deal_456",
            "recommended_action": "Investigate delay reason",
            "created_at": (datetime.utcnow() - timedelta(hours=12)).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "type": AlertType.ENGAGEMENT_LOW.value,
            "severity": "medium",
            "title": "Low engagement: Global Industries",
            "description": "Champion has not responded to last 3 emails",
            "deal_id": "deal_789",
            "recommended_action": "Try different contact or channel",
            "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        }
    ]
    
    if alert_type:
        mock_alerts = [a for a in mock_alerts if a["type"] == alert_type.value]
    
    return {
        "alerts": mock_alerts[:limit],
        "total": len(mock_alerts),
        "unread": len([a for a in mock_alerts if not a.get("read")])
    }


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, reason: Optional[str] = None):
    """Dismiss an alert"""
    return {
        "alert_id": alert_id,
        "status": "dismissed",
        "reason": reason,
        "dismissed_at": datetime.utcnow().isoformat()
    }


@router.put("/alerts/config")
async def update_alert_config(
    configs: List[AlertConfig],
    tenant_id: str = Query(default="default")
):
    """Update alert configurations"""
    saved_configs = []
    for config in configs:
        saved_config = {
            "alert_type": config.alert_type.value,
            "enabled": config.enabled,
            "threshold": config.threshold,
            "notify_via": config.notify_via,
            "updated_at": datetime.utcnow().isoformat()
        }
        saved_configs.append(saved_config)
    
    return {"configs": saved_configs}


# Analytics
@router.get("/analytics/win-loss")
async def get_win_loss_analysis(
    time_range: TimeRange = TimeRange.THIS_QUARTER,
    tenant_id: str = Query(default="default")
):
    """Get win/loss analysis"""
    return {
        "time_range": time_range.value,
        "summary": {
            "total_closed": 48,
            "won": 15,
            "lost": 33,
            "win_rate": 0.31,
            "avg_won_deal_size": 68000,
            "avg_lost_deal_size": 42000
        },
        "loss_reasons": [
            {"reason": "Price", "count": 12, "percentage": 36.4},
            {"reason": "Went with competitor", "count": 8, "percentage": 24.2},
            {"reason": "No decision", "count": 6, "percentage": 18.2},
            {"reason": "Timing", "count": 4, "percentage": 12.1},
            {"reason": "Other", "count": 3, "percentage": 9.1}
        ],
        "win_patterns": [
            {"pattern": "Executive sponsor engaged", "win_rate": 0.65},
            {"pattern": "Technical validation completed", "win_rate": 0.58},
            {"pattern": "3+ stakeholders in meetings", "win_rate": 0.52},
            {"pattern": "ROI quantified", "win_rate": 0.48}
        ],
        "competitor_analysis": [
            {"competitor": "Competitor A", "encounters": 15, "wins": 5, "win_rate": 0.33},
            {"competitor": "Competitor B", "encounters": 10, "wins": 4, "win_rate": 0.40},
            {"competitor": "Competitor C", "encounters": 8, "wins": 2, "win_rate": 0.25}
        ]
    }


@router.get("/analytics/rep-performance")
async def get_rep_performance(
    time_range: TimeRange = TimeRange.THIS_QUARTER,
    tenant_id: str = Query(default="default")
):
    """Get sales rep performance analysis"""
    return {
        "time_range": time_range.value,
        "reps": [
            {
                "rep_id": "rep_1",
                "name": "Alice Johnson",
                "quota": 1000000,
                "closed": 420000,
                "pipeline": 850000,
                "attainment": 42.0,
                "win_rate": 0.38,
                "avg_deal_size": 52500,
                "avg_sales_cycle": 38,
                "activities": {"calls": 120, "emails": 450, "meetings": 35}
            },
            {
                "rep_id": "rep_2",
                "name": "Bob Smith",
                "quota": 1000000,
                "closed": 380000,
                "pipeline": 720000,
                "attainment": 38.0,
                "win_rate": 0.32,
                "avg_deal_size": 47500,
                "avg_sales_cycle": 45,
                "activities": {"calls": 95, "emails": 380, "meetings": 28}
            },
            {
                "rep_id": "rep_3",
                "name": "Carol Davis",
                "quota": 1000000,
                "closed": 520000,
                "pipeline": 980000,
                "attainment": 52.0,
                "win_rate": 0.42,
                "avg_deal_size": 65000,
                "avg_sales_cycle": 35,
                "activities": {"calls": 145, "emails": 520, "meetings": 42}
            }
        ],
        "benchmarks": {
            "avg_attainment": 44.0,
            "avg_win_rate": 0.37,
            "avg_deal_size": 55000,
            "avg_sales_cycle": 39
        }
    }


# Snapshots
@router.post("/snapshots")
async def create_pipeline_snapshot(
    tenant_id: str = Query(default="default"),
    notes: Optional[str] = None
):
    """Create a pipeline snapshot for historical tracking"""
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    snapshot = {
        "id": snapshot_id,
        "tenant_id": tenant_id,
        "timestamp": now.isoformat(),
        "notes": notes,
        "metrics": {
            "total_pipeline": 4250000,
            "weighted_pipeline": 2125000,
            "deals_count": 85,
            "by_stage": [
                {"stage": "Discovery", "count": 25, "value": 750000},
                {"stage": "Qualification", "count": 20, "value": 1000000},
                {"stage": "Proposal", "count": 18, "value": 900000},
                {"stage": "Negotiation", "count": 15, "value": 1100000},
                {"stage": "Closing", "count": 7, "value": 500000}
            ],
            "commit_forecast": 1850000,
            "best_case_forecast": 2450000
        }
    }
    
    pipeline_snapshots[snapshot_id] = snapshot
    
    logger.info("pipeline_snapshot_created", snapshot_id=snapshot_id)
    return snapshot


@router.get("/snapshots")
async def list_snapshots(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=30, le=100),
    tenant_id: str = Query(default="default")
):
    """List pipeline snapshots"""
    result = [s for s in pipeline_snapshots.values() if s.get("tenant_id") == tenant_id]
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "snapshots": result[:limit],
        "total": len(result)
    }


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """Get a specific pipeline snapshot"""
    if snapshot_id not in pipeline_snapshots:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return pipeline_snapshots[snapshot_id]


@router.get("/snapshots/compare")
async def compare_snapshots(
    snapshot_1: str,
    snapshot_2: str
):
    """Compare two pipeline snapshots"""
    if snapshot_1 not in pipeline_snapshots:
        raise HTTPException(status_code=404, detail="Snapshot 1 not found")
    if snapshot_2 not in pipeline_snapshots:
        raise HTTPException(status_code=404, detail="Snapshot 2 not found")
    
    s1 = pipeline_snapshots[snapshot_1]
    s2 = pipeline_snapshots[snapshot_2]
    m1 = s1.get("metrics", {})
    m2 = s2.get("metrics", {})
    
    return {
        "snapshot_1": {"id": snapshot_1, "timestamp": s1.get("timestamp")},
        "snapshot_2": {"id": snapshot_2, "timestamp": s2.get("timestamp")},
        "changes": {
            "total_pipeline": {
                "from": m1.get("total_pipeline"),
                "to": m2.get("total_pipeline"),
                "change": m2.get("total_pipeline", 0) - m1.get("total_pipeline", 0)
            },
            "deals_count": {
                "from": m1.get("deals_count"),
                "to": m2.get("deals_count"),
                "change": m2.get("deals_count", 0) - m1.get("deals_count", 0)
            },
            "commit_forecast": {
                "from": m1.get("commit_forecast"),
                "to": m2.get("commit_forecast"),
                "change": m2.get("commit_forecast", 0) - m1.get("commit_forecast", 0)
            }
        }
    }
