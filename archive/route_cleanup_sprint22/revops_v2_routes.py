"""
Revenue Operations Routes - RevOps metrics, processes and automation
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

router = APIRouter(prefix="/revops-v2", tags=["Revenue Operations V2"])


class MetricCategory(str, Enum):
    PIPELINE = "pipeline"
    REVENUE = "revenue"
    EFFICIENCY = "efficiency"
    PRODUCTIVITY = "productivity"
    QUALITY = "quality"


class ProcessType(str, Enum):
    LEAD_MANAGEMENT = "lead_management"
    OPPORTUNITY_MANAGEMENT = "opportunity_management"
    FORECASTING = "forecasting"
    TERRITORY_MANAGEMENT = "territory_management"
    COMPENSATION = "compensation"
    DATA_GOVERNANCE = "data_governance"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# In-memory storage
revops_metrics = {}
revops_alerts = {}
process_health = {}
governance_rules = {}


class MetricDefinitionCreate(BaseModel):
    name: str
    category: MetricCategory
    formula: str
    target: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None


class GovernanceRuleCreate(BaseModel):
    name: str
    process_type: ProcessType
    rule_type: str  # validation, automation, enrichment
    conditions: Dict[str, Any]
    actions: List[str]
    is_active: bool = True


# Dashboard
@router.get("/dashboard")
async def get_revops_dashboard(
    period: str = Query(default="current_quarter"),
    tenant_id: str = Query(default="default")
):
    """Get comprehensive RevOps dashboard"""
    now = datetime.utcnow()
    
    return {
        "period": period,
        "generated_at": now.isoformat(),
        "executive_summary": {
            "revenue_attainment": round(random.uniform(0.75, 1.15), 2),
            "pipeline_coverage": round(random.uniform(2.5, 4.0), 1),
            "forecast_accuracy": round(random.uniform(0.80, 0.95), 2),
            "win_rate": round(random.uniform(0.20, 0.35), 2),
            "avg_deal_size": random.randint(35000, 75000),
            "sales_cycle_days": random.randint(35, 65)
        },
        "pipeline_health": {
            "total_pipeline": random.randint(5000000, 15000000),
            "qualified_pipeline": random.randint(3000000, 10000000),
            "commit_forecast": random.randint(1500000, 4000000),
            "weighted_pipeline": random.randint(2000000, 6000000),
            "pipeline_created_mtd": random.randint(500000, 2000000),
            "pipeline_closed_mtd": random.randint(300000, 1500000)
        },
        "efficiency_metrics": {
            "lead_to_opportunity_rate": round(random.uniform(0.15, 0.30), 2),
            "opportunity_to_close_rate": round(random.uniform(0.20, 0.35), 2),
            "avg_activities_per_won_deal": random.randint(25, 60),
            "cost_per_acquisition": random.randint(5000, 15000),
            "ltv_to_cac_ratio": round(random.uniform(3.0, 6.0), 1)
        },
        "team_performance": {
            "quota_attainment_avg": round(random.uniform(0.70, 1.10), 2),
            "reps_above_quota_pct": round(random.uniform(0.35, 0.55), 2),
            "activity_completion_rate": round(random.uniform(0.75, 0.95), 2),
            "forecast_accuracy_by_rep_avg": round(random.uniform(0.70, 0.90), 2)
        },
        "trends": {
            "revenue_vs_prior_quarter": round(random.uniform(-0.10, 0.25), 2),
            "pipeline_vs_prior_quarter": round(random.uniform(-0.05, 0.30), 2),
            "win_rate_vs_prior_quarter": round(random.uniform(-0.05, 0.10), 2)
        }
    }


# Key Metrics
@router.get("/metrics")
async def get_key_metrics(
    category: Optional[MetricCategory] = None,
    tenant_id: str = Query(default="default")
):
    """Get key RevOps metrics"""
    metrics = [
        {
            "name": "Annual Recurring Revenue (ARR)",
            "category": MetricCategory.REVENUE.value,
            "value": random.randint(5000000, 20000000),
            "target": random.randint(6000000, 22000000),
            "attainment": round(random.uniform(0.80, 1.10), 2),
            "trend": random.choice(["up", "down", "stable"]),
            "change_pct": round(random.uniform(-5, 15), 1)
        },
        {
            "name": "Net Revenue Retention (NRR)",
            "category": MetricCategory.REVENUE.value,
            "value": round(random.uniform(100, 130), 1),
            "target": 110,
            "attainment": round(random.uniform(0.90, 1.20), 2),
            "trend": "up",
            "change_pct": round(random.uniform(0, 10), 1)
        },
        {
            "name": "Pipeline Velocity",
            "category": MetricCategory.PIPELINE.value,
            "value": random.randint(500000, 2000000),
            "target": random.randint(600000, 2200000),
            "unit": "$ per month",
            "trend": random.choice(["up", "stable"]),
            "change_pct": round(random.uniform(-5, 15), 1)
        },
        {
            "name": "Sales Efficiency Ratio",
            "category": MetricCategory.EFFICIENCY.value,
            "value": round(random.uniform(0.8, 1.5), 2),
            "target": 1.0,
            "trend": random.choice(["up", "stable"]),
            "change_pct": round(random.uniform(-3, 8), 1)
        },
        {
            "name": "Quota Attainment",
            "category": MetricCategory.PRODUCTIVITY.value,
            "value": round(random.uniform(0.70, 1.10), 2),
            "target": 1.0,
            "trend": random.choice(["up", "down", "stable"]),
            "change_pct": round(random.uniform(-5, 10), 1)
        },
        {
            "name": "Data Quality Score",
            "category": MetricCategory.QUALITY.value,
            "value": random.randint(75, 95),
            "target": 90,
            "trend": "up",
            "change_pct": round(random.uniform(0, 5), 1)
        }
    ]
    
    if category:
        metrics = [m for m in metrics if m["category"] == category.value]
    
    return {"metrics": metrics, "total": len(metrics)}


@router.post("/metrics/define")
async def define_custom_metric(
    request: MetricDefinitionCreate,
    tenant_id: str = Query(default="default")
):
    """Define a custom metric"""
    metric_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    metric = {
        "id": metric_id,
        "name": request.name,
        "category": request.category.value,
        "formula": request.formula,
        "target": request.target,
        "warning_threshold": request.warning_threshold,
        "critical_threshold": request.critical_threshold,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    revops_metrics[metric_id] = metric
    
    return metric


# Process Health
@router.get("/process-health")
async def get_process_health(
    process_type: Optional[ProcessType] = None,
    tenant_id: str = Query(default="default")
):
    """Get health status of RevOps processes"""
    processes = [
        {
            "process": ProcessType.LEAD_MANAGEMENT.value,
            "health_score": random.randint(70, 95),
            "status": random.choice(["healthy", "needs_attention"]),
            "metrics": {
                "lead_response_time_hours": round(random.uniform(1, 8), 1),
                "lead_conversion_rate": round(random.uniform(0.15, 0.30), 2),
                "leads_processed_today": random.randint(20, 100)
            },
            "issues": ["Lead routing delays during peak hours"] if random.random() > 0.7 else []
        },
        {
            "process": ProcessType.OPPORTUNITY_MANAGEMENT.value,
            "health_score": random.randint(70, 95),
            "status": random.choice(["healthy", "needs_attention"]),
            "metrics": {
                "stage_update_compliance": round(random.uniform(0.75, 0.95), 2),
                "opportunity_hygiene_score": random.randint(70, 95),
                "stale_opportunities": random.randint(5, 25)
            },
            "issues": ["15 opportunities haven't been updated in 7+ days"] if random.random() > 0.6 else []
        },
        {
            "process": ProcessType.FORECASTING.value,
            "health_score": random.randint(70, 95),
            "status": random.choice(["healthy", "needs_attention"]),
            "metrics": {
                "forecast_submission_rate": round(random.uniform(0.85, 1.0), 2),
                "forecast_accuracy_30d": round(random.uniform(0.75, 0.92), 2),
                "commit_vs_actual_variance": round(random.uniform(0.05, 0.20), 2)
            },
            "issues": []
        },
        {
            "process": ProcessType.TERRITORY_MANAGEMENT.value,
            "health_score": random.randint(70, 95),
            "status": random.choice(["healthy", "needs_attention"]),
            "metrics": {
                "territory_coverage_rate": round(random.uniform(0.85, 0.98), 2),
                "balanced_territories_pct": round(random.uniform(0.70, 0.90), 2),
                "conflict_rate": round(random.uniform(0.01, 0.05), 3)
            },
            "issues": []
        },
        {
            "process": ProcessType.DATA_GOVERNANCE.value,
            "health_score": random.randint(70, 95),
            "status": random.choice(["healthy", "needs_attention"]),
            "metrics": {
                "data_completeness": round(random.uniform(0.80, 0.95), 2),
                "duplicate_rate": round(random.uniform(0.02, 0.08), 3),
                "validation_pass_rate": round(random.uniform(0.90, 0.99), 2)
            },
            "issues": ["Duplicate accounts detected in Northeast territory"] if random.random() > 0.7 else []
        }
    ]
    
    if process_type:
        processes = [p for p in processes if p["process"] == process_type.value]
    
    return {"processes": processes, "overall_health": random.randint(75, 92)}


# Alerts
@router.get("/alerts")
async def get_revops_alerts(
    severity: Optional[AlertSeverity] = None,
    acknowledged: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """Get RevOps alerts and issues"""
    alerts = [
        {
            "id": str(uuid.uuid4()),
            "severity": AlertSeverity.CRITICAL.value,
            "category": "pipeline",
            "title": "Pipeline coverage below threshold",
            "description": "Current quarter pipeline coverage is 2.3x, below the 3x threshold",
            "impact": "May miss quarterly target by $500K",
            "recommendation": "Accelerate pipeline generation campaigns",
            "created_at": datetime.utcnow().isoformat(),
            "acknowledged": False
        },
        {
            "id": str(uuid.uuid4()),
            "severity": AlertSeverity.HIGH.value,
            "category": "forecasting",
            "title": "Forecast accuracy declining",
            "description": "30-day forecast accuracy dropped to 72% from 85%",
            "impact": "Revenue predictability affected",
            "recommendation": "Review rep forecasting practices",
            "created_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
            "acknowledged": False
        },
        {
            "id": str(uuid.uuid4()),
            "severity": AlertSeverity.MEDIUM.value,
            "category": "data_quality",
            "title": "Account data quality issue",
            "description": "35% of new accounts missing industry classification",
            "impact": "Territory routing may be affected",
            "recommendation": "Enable auto-enrichment for new accounts",
            "created_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
            "acknowledged": True
        }
    ]
    
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity.value]
    if acknowledged is not None:
        alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
    
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    notes: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Acknowledge an alert"""
    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_at": datetime.utcnow().isoformat(),
        "notes": notes
    }


# Governance Rules
@router.post("/governance/rules")
async def create_governance_rule(
    request: GovernanceRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create a data governance rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "process_type": request.process_type.value,
        "rule_type": request.rule_type,
        "conditions": request.conditions,
        "actions": request.actions,
        "is_active": request.is_active,
        "executions": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    governance_rules[rule_id] = rule
    
    return rule


@router.get("/governance/rules")
async def list_governance_rules(
    process_type: Optional[ProcessType] = None,
    active_only: bool = True,
    tenant_id: str = Query(default="default")
):
    """List governance rules"""
    result = [r for r in governance_rules.values() if r.get("tenant_id") == tenant_id]
    
    if process_type:
        result = [r for r in result if r.get("process_type") == process_type.value]
    if active_only:
        result = [r for r in result if r.get("is_active", True)]
    
    return {"rules": result, "total": len(result)}


# Funnel Analysis
@router.get("/funnel")
async def get_funnel_analysis(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get sales funnel analysis"""
    return {
        "period": period,
        "funnel_stages": [
            {"stage": "Leads", "count": random.randint(2000, 5000), "value": None},
            {"stage": "MQLs", "count": random.randint(800, 2000), "value": None, "conversion_rate": round(random.uniform(0.35, 0.50), 2)},
            {"stage": "SQLs", "count": random.randint(300, 800), "value": None, "conversion_rate": round(random.uniform(0.35, 0.45), 2)},
            {"stage": "Opportunities", "count": random.randint(150, 400), "value": random.randint(5000000, 15000000), "conversion_rate": round(random.uniform(0.45, 0.55), 2)},
            {"stage": "Proposals", "count": random.randint(80, 200), "value": random.randint(3000000, 8000000), "conversion_rate": round(random.uniform(0.50, 0.60), 2)},
            {"stage": "Closed Won", "count": random.randint(25, 80), "value": random.randint(1000000, 3000000), "conversion_rate": round(random.uniform(0.25, 0.40), 2)}
        ],
        "overall_conversion": round(random.uniform(0.01, 0.03), 3),
        "avg_time_to_close_days": random.randint(35, 65),
        "bottlenecks": [
            {"stage": "SQL to Opportunity", "issue": "Low conversion rate", "recommendation": "Improve qualification criteria"}
        ]
    }


# Capacity Planning
@router.get("/capacity")
async def get_capacity_analysis(
    tenant_id: str = Query(default="default")
):
    """Get sales capacity analysis"""
    return {
        "current_headcount": {
            "aes": random.randint(15, 40),
            "sdrs": random.randint(8, 25),
            "ses": random.randint(5, 15)
        },
        "capacity_analysis": {
            "current_quota_capacity": random.randint(8000000, 20000000),
            "target_revenue": random.randint(10000000, 25000000),
            "capacity_gap": random.randint(-2000000, 2000000),
            "capacity_utilization": round(random.uniform(0.80, 1.15), 2)
        },
        "hiring_recommendations": {
            "aes_needed": random.randint(0, 5),
            "sdrs_needed": random.randint(0, 3),
            "ramp_time_months": 6,
            "revenue_per_ae": random.randint(500000, 1200000)
        },
        "productivity_metrics": {
            "avg_quota_per_ae": random.randint(400000, 800000),
            "avg_pipeline_per_sdr": random.randint(1000000, 3000000),
            "ae_to_sdr_ratio": round(random.uniform(1.5, 3.0), 1)
        }
    }


# Trend Analysis
@router.get("/trends")
async def get_revops_trends(
    periods: int = Query(default=6, ge=3, le=12),
    metric: str = Query(default="revenue"),
    tenant_id: str = Query(default="default")
):
    """Get RevOps trend analysis"""
    now = datetime.utcnow()
    trends = []
    
    base_value = random.randint(1000000, 3000000)
    for i in range(periods):
        period_date = now - timedelta(days=30 * i)
        value = base_value * (1 + random.uniform(-0.1, 0.15))
        trends.append({
            "period": period_date.strftime("%Y-%m"),
            "value": int(value),
            "change_pct": round(random.uniform(-10, 15), 1),
            "forecast": int(value * 1.1) if i < 3 else None
        })
        base_value = value
    
    return {
        "metric": metric,
        "trends": list(reversed(trends)),
        "overall_trend": random.choice(["growing", "stable", "declining"]),
        "growth_rate_avg": round(random.uniform(5, 20), 1)
    }
