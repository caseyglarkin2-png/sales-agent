"""
Revenue Operations Routes - RevOps and revenue process optimization
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

router = APIRouter(prefix="/revops", tags=["Revenue Operations"])


class ProcessType(str, Enum):
    LEAD_TO_OPPORTUNITY = "lead_to_opportunity"
    OPPORTUNITY_TO_CLOSE = "opportunity_to_close"
    QUOTE_TO_CASH = "quote_to_cash"
    RENEWAL = "renewal"
    EXPANSION = "expansion"
    HANDOFF = "handoff"


class ProcessStatus(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricType(str, Enum):
    CONVERSION_RATE = "conversion_rate"
    VELOCITY = "velocity"
    WIN_RATE = "win_rate"
    ASP = "asp"
    CAC = "cac"
    LTV = "ltv"
    PIPELINE_COVERAGE = "pipeline_coverage"
    FORECAST_ACCURACY = "forecast_accuracy"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class HandoffType(str, Enum):
    SDR_TO_AE = "sdr_to_ae"
    AE_TO_CSM = "ae_to_csm"
    MARKETING_TO_SDR = "marketing_to_sdr"
    CSM_TO_AM = "csm_to_am"


class FunnelStage(str, Enum):
    LEAD = "lead"
    MQL = "mql"
    SQL = "sql"
    SAL = "sal"
    OPPORTUNITY = "opportunity"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"


# In-memory storage
processes = {}
process_metrics = {}
revops_alerts = {}
handoffs = {}
funnel_snapshots = {}
forecasts = {}
targets = {}
attribution_data = {}
data_quality_issues = {}


# Revenue Processes
@router.post("/processes")
async def create_process(
    name: str,
    process_type: ProcessType,
    stages: List[Dict[str, Any]],
    owner_id: Optional[str] = None,
    description: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a revenue process definition"""
    process_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    process = {
        "id": process_id,
        "name": name,
        "process_type": process_type.value,
        "description": description,
        "stages": stages,
        "owner_id": owner_id,
        "status": ProcessStatus.UNKNOWN.value,
        "health_score": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    processes[process_id] = process
    
    logger.info("revops_process_created", process_id=process_id, type=process_type.value)
    return process


@router.get("/processes")
async def list_processes(
    process_type: Optional[ProcessType] = None,
    status: Optional[ProcessStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List revenue processes"""
    result = [p for p in processes.values() if p.get("tenant_id") == tenant_id]
    
    if process_type:
        result = [p for p in result if p.get("process_type") == process_type.value]
    if status:
        result = [p for p in result if p.get("status") == status.value]
    
    return {"processes": result, "total": len(result)}


@router.get("/processes/{process_id}")
async def get_process(process_id: str):
    """Get process details"""
    if process_id not in processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    process = processes[process_id]
    metrics = process_metrics.get(process_id, {})
    
    return {
        **process,
        "metrics": metrics,
        "bottlenecks": identify_bottlenecks(process),
        "optimization_suggestions": generate_suggestions(process)
    }


@router.get("/processes/{process_id}/analyze")
async def analyze_process(
    process_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Analyze process performance"""
    if process_id not in processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    process = processes[process_id]
    
    # Generate stage analysis
    stage_analysis = []
    for i, stage in enumerate(process.get("stages", [])):
        stage_analysis.append({
            "stage": stage.get("name", f"Stage {i+1}"),
            "avg_time_days": random.uniform(1, 10),
            "conversion_rate": random.uniform(0.4, 0.9),
            "records_in_stage": random.randint(10, 100),
            "stuck_records": random.randint(0, 20),
            "trend": random.choice(["improving", "declining", "stable"])
        })
    
    return {
        "process_id": process_id,
        "process_name": process["name"],
        "overall_health": random.choice(["healthy", "at_risk", "critical"]),
        "total_velocity_days": sum(s["avg_time_days"] for s in stage_analysis),
        "end_to_end_conversion": random.uniform(0.1, 0.4),
        "stage_analysis": stage_analysis,
        "period": {"start_date": start_date, "end_date": end_date}
    }


# Funnel Analytics
@router.get("/funnel")
async def get_funnel_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    segment: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get full funnel metrics"""
    stages = [
        {
            "stage": FunnelStage.LEAD.value,
            "count": random.randint(1000, 5000),
            "value": 0
        },
        {
            "stage": FunnelStage.MQL.value,
            "count": random.randint(400, 2000),
            "value": 0
        },
        {
            "stage": FunnelStage.SQL.value,
            "count": random.randint(200, 1000),
            "value": 0
        },
        {
            "stage": FunnelStage.SAL.value,
            "count": random.randint(100, 500),
            "value": 0
        },
        {
            "stage": FunnelStage.OPPORTUNITY.value,
            "count": random.randint(80, 400),
            "value": random.randint(500000, 2000000)
        },
        {
            "stage": FunnelStage.PROPOSAL.value,
            "count": random.randint(50, 200),
            "value": random.randint(300000, 1000000)
        },
        {
            "stage": FunnelStage.NEGOTIATION.value,
            "count": random.randint(30, 100),
            "value": random.randint(200000, 800000)
        },
        {
            "stage": FunnelStage.CLOSED_WON.value,
            "count": random.randint(15, 50),
            "value": random.randint(100000, 500000)
        }
    ]
    
    # Calculate conversions
    for i in range(1, len(stages)):
        stages[i]["conversion_from_prev"] = round(
            stages[i]["count"] / max(1, stages[i-1]["count"]), 3
        )
    stages[0]["conversion_from_prev"] = 1.0
    
    return {
        "funnel_stages": stages,
        "lead_to_won_rate": round(stages[-1]["count"] / max(1, stages[0]["count"]), 4),
        "avg_deal_size": round(stages[-1]["value"] / max(1, stages[-1]["count"]), 2),
        "period": {"start_date": start_date, "end_date": end_date},
        "segment": segment
    }


@router.post("/funnel/snapshot")
async def save_funnel_snapshot(
    name: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Save current funnel snapshot for comparison"""
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Get current funnel
    funnel = await get_funnel_metrics(tenant_id=tenant_id)
    
    snapshot = {
        "id": snapshot_id,
        "name": name or f"Snapshot {now.isoformat()[:10]}",
        "funnel_data": funnel,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    funnel_snapshots[snapshot_id] = snapshot
    
    return snapshot


@router.get("/funnel/compare")
async def compare_funnel_periods(
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    tenant_id: str = Query(default="default")
):
    """Compare funnel metrics between periods"""
    period1 = await get_funnel_metrics(start_date=period1_start, end_date=period1_end, tenant_id=tenant_id)
    period2 = await get_funnel_metrics(start_date=period2_start, end_date=period2_end, tenant_id=tenant_id)
    
    comparison = []
    for i, stage in enumerate(period1["funnel_stages"]):
        p2_stage = period2["funnel_stages"][i]
        comparison.append({
            "stage": stage["stage"],
            "period1_count": stage["count"],
            "period2_count": p2_stage["count"],
            "count_change_pct": round((p2_stage["count"] - stage["count"]) / max(1, stage["count"]), 3),
            "period1_conversion": stage.get("conversion_from_prev", 0),
            "period2_conversion": p2_stage.get("conversion_from_prev", 0)
        })
    
    return {
        "period1": {"start": period1_start, "end": period1_end},
        "period2": {"start": period2_start, "end": period2_end},
        "comparison": comparison,
        "overall_trend": "improving" if period2["lead_to_won_rate"] > period1["lead_to_won_rate"] else "declining"
    }


# Handoff Management
@router.post("/handoffs")
async def create_handoff(
    handoff_type: HandoffType,
    record_id: str,
    record_type: str,
    from_user_id: str,
    to_user_id: str,
    notes: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    tenant_id: str = Query(default="default")
):
    """Create a handoff record"""
    handoff_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    handoff = {
        "id": handoff_id,
        "handoff_type": handoff_type.value,
        "record_id": record_id,
        "record_type": record_type,
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "notes": notes,
        "context": context or {},
        "status": "pending",
        "accepted_at": None,
        "sla_hours": 24,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    handoffs[handoff_id] = handoff
    
    logger.info("handoff_created", handoff_id=handoff_id, type=handoff_type.value)
    return handoff


@router.post("/handoffs/{handoff_id}/accept")
async def accept_handoff(
    handoff_id: str,
    user_id: str = Query(default="default")
):
    """Accept a handoff"""
    if handoff_id not in handoffs:
        raise HTTPException(status_code=404, detail="Handoff not found")
    
    handoff = handoffs[handoff_id]
    now = datetime.utcnow()
    
    handoff["status"] = "accepted"
    handoff["accepted_at"] = now.isoformat()
    handoff["accepted_by"] = user_id
    
    # Calculate SLA compliance
    created = datetime.fromisoformat(handoff["created_at"])
    hours_elapsed = (now - created).total_seconds() / 3600
    handoff["sla_met"] = hours_elapsed <= handoff["sla_hours"]
    
    return handoff


@router.get("/handoffs/metrics")
async def get_handoff_metrics(
    handoff_type: Optional[HandoffType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get handoff metrics"""
    result = [h for h in handoffs.values() if h.get("tenant_id") == tenant_id]
    
    if handoff_type:
        result = [h for h in result if h.get("handoff_type") == handoff_type.value]
    
    total = len(result)
    accepted = len([h for h in result if h.get("status") == "accepted"])
    sla_met = len([h for h in result if h.get("sla_met")])
    
    return {
        "total_handoffs": total,
        "accepted": accepted,
        "pending": total - accepted,
        "acceptance_rate": round(accepted / max(1, total), 3),
        "sla_compliance": round(sla_met / max(1, accepted), 3),
        "avg_acceptance_time_hours": random.uniform(2, 12),
        "by_type": {
            ht.value: len([h for h in result if h.get("handoff_type") == ht.value])
            for ht in HandoffType
        }
    }


# Alerts
@router.post("/alerts")
async def create_alert(
    title: str,
    severity: AlertSeverity,
    metric_type: MetricType,
    threshold_value: float,
    current_value: float,
    message: Optional[str] = None,
    affected_area: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create a RevOps alert"""
    alert_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    alert = {
        "id": alert_id,
        "title": title,
        "severity": severity.value,
        "metric_type": metric_type.value,
        "threshold_value": threshold_value,
        "current_value": current_value,
        "deviation_pct": round((current_value - threshold_value) / max(0.001, threshold_value), 3),
        "message": message,
        "affected_area": affected_area,
        "status": "active",
        "acknowledged_at": None,
        "resolved_at": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    revops_alerts[alert_id] = alert
    
    return alert


@router.get("/alerts")
async def list_alerts(
    severity: Optional[AlertSeverity] = None,
    status: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List RevOps alerts"""
    result = [a for a in revops_alerts.values() if a.get("tenant_id") == tenant_id]
    
    if severity:
        result = [a for a in result if a.get("severity") == severity.value]
    if status:
        result = [a for a in result if a.get("status") == status]
    
    result.sort(key=lambda x: (
        {"critical": 0, "warning": 1, "info": 2}.get(x.get("severity", "info"), 2),
        x.get("created_at", "")
    ))
    
    return {"alerts": result, "total": len(result)}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user_id: str = Query(default="default")
):
    """Acknowledge an alert"""
    if alert_id not in revops_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = revops_alerts[alert_id]
    alert["status"] = "acknowledged"
    alert["acknowledged_at"] = datetime.utcnow().isoformat()
    alert["acknowledged_by"] = user_id
    
    return alert


# Targets & Quotas
@router.post("/targets")
async def set_target(
    metric_type: MetricType,
    target_value: float,
    period: str,
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Set a target"""
    target_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    target = {
        "id": target_id,
        "metric_type": metric_type.value,
        "target_value": target_value,
        "period": period,
        "team_id": team_id,
        "user_id": user_id,
        "current_value": None,
        "attainment_pct": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    targets[target_id] = target
    
    return target


@router.get("/targets")
async def get_targets(
    period: Optional[str] = None,
    metric_type: Optional[MetricType] = None,
    team_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get targets"""
    result = [t for t in targets.values() if t.get("tenant_id") == tenant_id]
    
    if period:
        result = [t for t in result if t.get("period") == period]
    if metric_type:
        result = [t for t in result if t.get("metric_type") == metric_type.value]
    if team_id:
        result = [t for t in result if t.get("team_id") == team_id]
    
    # Add mock current values
    for target in result:
        target["current_value"] = target["target_value"] * random.uniform(0.6, 1.2)
        target["attainment_pct"] = round(target["current_value"] / target["target_value"], 3)
    
    return {"targets": result, "total": len(result)}


# Attribution
@router.post("/attribution/record")
async def record_attribution(
    opportunity_id: str,
    touchpoints: List[Dict[str, Any]],
    model: str = "linear",
    tenant_id: str = Query(default="default")
):
    """Record attribution data"""
    now = datetime.utcnow()
    
    # Calculate attribution based on model
    total_credit = 1.0
    if model == "first_touch":
        for i, tp in enumerate(touchpoints):
            tp["credit"] = 1.0 if i == 0 else 0.0
    elif model == "last_touch":
        for i, tp in enumerate(touchpoints):
            tp["credit"] = 1.0 if i == len(touchpoints) - 1 else 0.0
    elif model == "linear":
        credit_per = total_credit / max(1, len(touchpoints))
        for tp in touchpoints:
            tp["credit"] = round(credit_per, 3)
    elif model == "time_decay":
        decay_factor = 0.7
        weights = [decay_factor ** (len(touchpoints) - i - 1) for i in range(len(touchpoints))]
        total_weight = sum(weights)
        for i, tp in enumerate(touchpoints):
            tp["credit"] = round(weights[i] / total_weight, 3)
    elif model == "u_shaped":
        if len(touchpoints) >= 2:
            touchpoints[0]["credit"] = 0.4
            touchpoints[-1]["credit"] = 0.4
            middle_credit = 0.2 / max(1, len(touchpoints) - 2)
            for i in range(1, len(touchpoints) - 1):
                touchpoints[i]["credit"] = round(middle_credit, 3)
        else:
            for tp in touchpoints:
                tp["credit"] = 1.0 / len(touchpoints)
    
    attribution = {
        "opportunity_id": opportunity_id,
        "model": model,
        "touchpoints": touchpoints,
        "tenant_id": tenant_id,
        "recorded_at": now.isoformat()
    }
    
    attribution_data[opportunity_id] = attribution
    
    return attribution


@router.get("/attribution/channel-effectiveness")
async def get_channel_effectiveness(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: str = "linear",
    tenant_id: str = Query(default="default")
):
    """Get channel effectiveness analysis"""
    channels = ["organic_search", "paid_search", "email", "social", "referral", "direct", "events", "content"]
    
    effectiveness = []
    for channel in channels:
        influenced_revenue = random.randint(100000, 1000000)
        spend = random.randint(10000, 100000)
        
        effectiveness.append({
            "channel": channel,
            "influenced_revenue": influenced_revenue,
            "influenced_opportunities": random.randint(10, 100),
            "influenced_won": random.randint(5, 50),
            "spend": spend,
            "roi": round(influenced_revenue / max(1, spend), 2),
            "avg_touchpoints": round(random.uniform(1, 5), 1),
            "first_touch_credit": round(random.uniform(0.1, 0.3), 3),
            "last_touch_credit": round(random.uniform(0.1, 0.3), 3)
        })
    
    effectiveness.sort(key=lambda x: x["influenced_revenue"], reverse=True)
    
    return {
        "model": model,
        "channel_effectiveness": effectiveness,
        "period": {"start_date": start_date, "end_date": end_date}
    }


# Data Quality
@router.get("/data-quality/score")
async def get_data_quality_score(tenant_id: str = Query(default="default")):
    """Get overall data quality score"""
    dimensions = {
        "completeness": random.uniform(0.7, 0.95),
        "accuracy": random.uniform(0.8, 0.98),
        "consistency": random.uniform(0.75, 0.95),
        "timeliness": random.uniform(0.8, 0.99),
        "uniqueness": random.uniform(0.85, 0.99)
    }
    
    overall_score = sum(dimensions.values()) / len(dimensions)
    
    return {
        "overall_score": round(overall_score, 3),
        "dimensions": {k: round(v, 3) for k, v in dimensions.items()},
        "trend": random.choice(["improving", "declining", "stable"]),
        "issues_count": random.randint(10, 100),
        "critical_issues": random.randint(0, 10)
    }


@router.get("/data-quality/issues")
async def get_data_quality_issues(
    severity: Optional[str] = None,
    object_type: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get data quality issues"""
    issues = []
    issue_types = [
        ("Missing required fields", "completeness", "medium"),
        ("Duplicate records", "uniqueness", "high"),
        ("Invalid email formats", "accuracy", "medium"),
        ("Stale data", "timeliness", "low"),
        ("Inconsistent naming", "consistency", "low"),
        ("Orphaned records", "integrity", "high")
    ]
    
    for issue_type, dimension, sev in issue_types:
        if severity and sev != severity:
            continue
        
        issues.append({
            "issue_type": issue_type,
            "dimension": dimension,
            "severity": sev,
            "affected_records": random.randint(10, 500),
            "object_type": object_type or random.choice(["contact", "account", "opportunity"]),
            "first_detected": datetime.utcnow().isoformat(),
            "auto_fixable": random.choice([True, False])
        })
    
    return {"issues": issues, "total": len(issues)}


# Reporting
@router.get("/reports/executive-summary")
async def get_executive_summary(
    period: str = Query(default="quarter"),
    tenant_id: str = Query(default="default")
):
    """Get executive summary report"""
    return {
        "period": period,
        "revenue": {
            "closed_won": random.randint(500000, 2000000),
            "target": random.randint(1000000, 3000000),
            "attainment_pct": random.uniform(0.7, 1.1),
            "vs_last_period": random.uniform(-0.1, 0.2)
        },
        "pipeline": {
            "total_value": random.randint(2000000, 8000000),
            "weighted_value": random.randint(1000000, 4000000),
            "coverage_ratio": random.uniform(2.5, 4.5),
            "deals_count": random.randint(50, 200)
        },
        "velocity": {
            "avg_cycle_days": random.randint(30, 90),
            "trend": random.choice(["faster", "slower", "stable"])
        },
        "conversion": {
            "lead_to_opportunity": random.uniform(0.1, 0.3),
            "opportunity_to_close": random.uniform(0.2, 0.4)
        },
        "health_indicators": {
            "pipeline_health": random.choice(["healthy", "at_risk", "critical"]),
            "forecast_confidence": random.choice(["high", "medium", "low"]),
            "process_efficiency": random.choice(["optimized", "adequate", "needs_work"])
        },
        "generated_at": datetime.utcnow().isoformat()
    }


# Helper functions
def identify_bottlenecks(process: Dict) -> List[Dict]:
    """Identify process bottlenecks"""
    bottlenecks = []
    
    for i, stage in enumerate(process.get("stages", [])):
        if random.random() > 0.7:
            bottlenecks.append({
                "stage": stage.get("name", f"Stage {i+1}"),
                "issue": random.choice([
                    "High drop-off rate",
                    "Long cycle time",
                    "Low conversion",
                    "Manual steps slowing process"
                ]),
                "impact": random.choice(["high", "medium", "low"]),
                "records_affected": random.randint(10, 100)
            })
    
    return bottlenecks


def generate_suggestions(process: Dict) -> List[Dict]:
    """Generate optimization suggestions"""
    suggestions = [
        {
            "title": "Automate stage transitions",
            "description": "Implement automatic stage updates based on activities",
            "estimated_impact": "15% faster cycle time",
            "effort": "medium"
        },
        {
            "title": "Add SLA tracking",
            "description": "Set up SLAs for each stage with alerts",
            "estimated_impact": "20% fewer stuck deals",
            "effort": "low"
        },
        {
            "title": "Implement lead scoring",
            "description": "Prioritize high-quality leads automatically",
            "estimated_impact": "25% better conversion",
            "effort": "high"
        }
    ]
    
    return random.sample(suggestions, k=min(len(suggestions), 2))
