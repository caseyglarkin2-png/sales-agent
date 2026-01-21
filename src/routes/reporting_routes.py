"""
Reporting Routes - Advanced report generation and distribution
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/reporting", tags=["Reporting"])


class ReportType(str, Enum):
    SALES_PERFORMANCE = "sales_performance"
    PIPELINE_ANALYSIS = "pipeline_analysis"
    REVENUE_FORECAST = "revenue_forecast"
    ACTIVITY_SUMMARY = "activity_summary"
    LEAD_SOURCE = "lead_source"
    CONVERSION_FUNNEL = "conversion_funnel"
    TEAM_PRODUCTIVITY = "team_productivity"
    QUOTA_ATTAINMENT = "quota_attainment"
    DEAL_VELOCITY = "deal_velocity"
    WIN_LOSS = "win_loss"
    CUSTOMER_HEALTH = "customer_health"
    ENGAGEMENT_METRICS = "engagement_metrics"
    CAMPAIGN_ROI = "campaign_roi"
    TERRITORY_PERFORMANCE = "territory_performance"
    PRODUCT_MIX = "product_mix"
    COMMISSION_SUMMARY = "commission_summary"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    HTML = "html"


class ReportSchedule(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ReportStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportCreate(BaseModel):
    name: str
    report_type: ReportType
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None  # date_range, filters, grouping, etc.
    format: ReportFormat = ReportFormat.JSON
    include_charts: bool = False
    recipients: Optional[List[str]] = None  # Email addresses for delivery


class ReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    format: Optional[ReportFormat] = None


class ScheduledReportCreate(BaseModel):
    name: str
    report_type: ReportType
    schedule: ReportSchedule
    parameters: Optional[Dict[str, Any]] = None
    format: ReportFormat = ReportFormat.PDF
    recipients: List[str]
    send_time: str = "08:00"  # HH:MM format
    timezone: str = "UTC"
    send_if_empty: bool = False


class DashboardWidget(BaseModel):
    widget_type: str  # chart, metric, table, etc.
    report_type: ReportType
    parameters: Optional[Dict[str, Any]] = None
    position: Dict[str, int]  # x, y, width, height
    title: Optional[str] = None
    refresh_interval_seconds: int = 300


class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    widgets: List[DashboardWidget]
    is_default: bool = False
    shared_with: Optional[List[str]] = None


# In-memory storage
reports = {}
scheduled_reports = {}
dashboards = {}
report_templates = {}


@router.post("/generate")
async def generate_report(
    request: ReportCreate,
    tenant_id: str = Query(default="default")
):
    """Generate a report"""
    import uuid
    
    report_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate report data based on type
    report_data = _generate_report_data(request.report_type, request.parameters or {})
    
    report = {
        "id": report_id,
        "name": request.name,
        "report_type": request.report_type.value,
        "description": request.description,
        "parameters": request.parameters or {},
        "format": request.format.value,
        "include_charts": request.include_charts,
        "status": ReportStatus.COMPLETED.value,
        "data": report_data,
        "row_count": len(report_data.get("rows", [])),
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "download_url": f"/reporting/download/{report_id}",
        "recipients": request.recipients or [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    reports[report_id] = report
    logger.info("report_generated", report_id=report_id, type=request.report_type.value)
    return report


def _generate_report_data(report_type: ReportType, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate mock report data based on type"""
    now = datetime.utcnow()
    
    if report_type == ReportType.SALES_PERFORMANCE:
        return {
            "summary": {
                "total_revenue": 1250000,
                "deals_won": 45,
                "deals_lost": 12,
                "win_rate": 78.9,
                "average_deal_size": 27778
            },
            "by_rep": [
                {"rep": "John Smith", "revenue": 350000, "deals": 12, "win_rate": 85},
                {"rep": "Jane Doe", "revenue": 420000, "deals": 15, "win_rate": 82},
                {"rep": "Bob Wilson", "revenue": 280000, "deals": 10, "win_rate": 75},
                {"rep": "Alice Brown", "revenue": 200000, "deals": 8, "win_rate": 72}
            ],
            "trend": [
                {"month": "Jan", "revenue": 180000},
                {"month": "Feb", "revenue": 220000},
                {"month": "Mar", "revenue": 250000},
                {"month": "Apr", "revenue": 200000},
                {"month": "May", "revenue": 280000},
                {"month": "Jun", "revenue": 120000}
            ],
            "rows": []
        }
    
    elif report_type == ReportType.PIPELINE_ANALYSIS:
        return {
            "summary": {
                "total_pipeline": 4500000,
                "weighted_pipeline": 2250000,
                "deals_in_pipeline": 85,
                "average_age_days": 28
            },
            "by_stage": [
                {"stage": "Qualification", "count": 25, "value": 750000, "probability": 10},
                {"stage": "Discovery", "count": 20, "value": 1200000, "probability": 25},
                {"stage": "Proposal", "count": 18, "value": 1500000, "probability": 50},
                {"stage": "Negotiation", "count": 12, "value": 800000, "probability": 75},
                {"stage": "Closing", "count": 10, "value": 250000, "probability": 90}
            ],
            "rows": []
        }
    
    elif report_type == ReportType.CONVERSION_FUNNEL:
        return {
            "funnel": [
                {"stage": "Leads", "count": 1000, "conversion_rate": 100},
                {"stage": "MQL", "count": 350, "conversion_rate": 35},
                {"stage": "SQL", "count": 175, "conversion_rate": 50},
                {"stage": "Opportunity", "count": 88, "conversion_rate": 50},
                {"stage": "Customer", "count": 35, "conversion_rate": 40}
            ],
            "overall_conversion": 3.5,
            "rows": []
        }
    
    elif report_type == ReportType.TEAM_PRODUCTIVITY:
        return {
            "summary": {
                "total_activities": 2500,
                "calls_made": 800,
                "emails_sent": 1200,
                "meetings_held": 350,
                "tasks_completed": 150
            },
            "by_rep": [
                {"rep": "John Smith", "calls": 200, "emails": 300, "meetings": 85, "tasks": 40},
                {"rep": "Jane Doe", "calls": 220, "emails": 350, "meetings": 95, "tasks": 45},
                {"rep": "Bob Wilson", "calls": 180, "emails": 280, "meetings": 80, "tasks": 35},
                {"rep": "Alice Brown", "calls": 200, "emails": 270, "meetings": 90, "tasks": 30}
            ],
            "rows": []
        }
    
    else:
        return {
            "summary": {"generated_at": now.isoformat()},
            "rows": []
        }


@router.get("/")
async def list_reports(
    report_type: Optional[ReportType] = None,
    status: Optional[ReportStatus] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List generated reports"""
    result = [r for r in reports.values() if r.get("tenant_id") == tenant_id]
    
    if report_type:
        result = [r for r in result if r.get("report_type") == report_type.value]
    if status:
        result = [r for r in result if r.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "reports": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report details"""
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    return reports[report_id]


@router.get("/download/{report_id}")
async def download_report(report_id: str, format: Optional[ReportFormat] = None):
    """Download report in specified format"""
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = reports[report_id]
    output_format = format.value if format else report.get("format", "json")
    
    return {
        "report_id": report_id,
        "format": output_format,
        "download_url": f"/reporting/files/{report_id}.{output_format}",
        "expires_at": report.get("expires_at"),
        "content_type": {
            "json": "application/json",
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pdf": "application/pdf",
            "html": "text/html"
        }.get(output_format, "application/octet-stream")
    }


@router.post("/{report_id}/refresh")
async def refresh_report(report_id: str):
    """Refresh report data"""
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = reports[report_id]
    now = datetime.utcnow()
    
    # Regenerate data
    report_data = _generate_report_data(
        ReportType(report["report_type"]),
        report.get("parameters", {})
    )
    
    report["data"] = report_data
    report["row_count"] = len(report_data.get("rows", []))
    report["generated_at"] = now.isoformat()
    report["expires_at"] = (now + timedelta(days=7)).isoformat()
    
    logger.info("report_refreshed", report_id=report_id)
    return report


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """Delete a report"""
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    del reports[report_id]
    logger.info("report_deleted", report_id=report_id)
    return {"status": "deleted", "report_id": report_id}


@router.post("/{report_id}/share")
async def share_report(
    report_id: str,
    recipients: List[str],
    message: Optional[str] = None
):
    """Share report via email"""
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = reports[report_id]
    
    logger.info("report_shared", report_id=report_id, recipients=len(recipients))
    return {
        "status": "shared",
        "report_id": report_id,
        "recipients": recipients,
        "shared_at": datetime.utcnow().isoformat()
    }


# Scheduled Reports
@router.post("/scheduled")
async def create_scheduled_report(
    request: ScheduledReportCreate,
    tenant_id: str = Query(default="default")
):
    """Create a scheduled report"""
    import uuid
    
    schedule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Calculate next run time
    next_run = _calculate_next_run(request.schedule, request.send_time, request.timezone)
    
    scheduled = {
        "id": schedule_id,
        "name": request.name,
        "report_type": request.report_type.value,
        "schedule": request.schedule.value,
        "parameters": request.parameters or {},
        "format": request.format.value,
        "recipients": request.recipients,
        "send_time": request.send_time,
        "timezone": request.timezone,
        "send_if_empty": request.send_if_empty,
        "is_active": True,
        "next_run": next_run.isoformat(),
        "last_run": None,
        "run_count": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    scheduled_reports[schedule_id] = scheduled
    logger.info("scheduled_report_created", schedule_id=schedule_id, schedule=request.schedule.value)
    return scheduled


def _calculate_next_run(schedule: ReportSchedule, send_time: str, timezone: str) -> datetime:
    """Calculate next run time for schedule"""
    now = datetime.utcnow()
    hour, minute = map(int, send_time.split(":"))
    
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if next_run <= now:
        if schedule == ReportSchedule.DAILY:
            next_run += timedelta(days=1)
        elif schedule == ReportSchedule.WEEKLY:
            next_run += timedelta(days=7)
        elif schedule == ReportSchedule.BIWEEKLY:
            next_run += timedelta(days=14)
        elif schedule == ReportSchedule.MONTHLY:
            next_run += timedelta(days=30)
        elif schedule == ReportSchedule.QUARTERLY:
            next_run += timedelta(days=90)
    
    return next_run


@router.get("/scheduled")
async def list_scheduled_reports(
    is_active: Optional[bool] = None,
    schedule: Optional[ReportSchedule] = None,
    tenant_id: str = Query(default="default")
):
    """List scheduled reports"""
    result = [s for s in scheduled_reports.values() if s.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [s for s in result if s.get("is_active") == is_active]
    if schedule:
        result = [s for s in result if s.get("schedule") == schedule.value]
    
    return {"scheduled_reports": result, "total": len(result)}


@router.get("/scheduled/{schedule_id}")
async def get_scheduled_report(schedule_id: str):
    """Get scheduled report details"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    return scheduled_reports[schedule_id]


@router.put("/scheduled/{schedule_id}")
async def update_scheduled_report(schedule_id: str, request: ScheduledReportCreate):
    """Update scheduled report"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    scheduled = scheduled_reports[schedule_id]
    scheduled.update({
        "name": request.name,
        "report_type": request.report_type.value,
        "schedule": request.schedule.value,
        "parameters": request.parameters or {},
        "format": request.format.value,
        "recipients": request.recipients,
        "send_time": request.send_time,
        "timezone": request.timezone,
        "send_if_empty": request.send_if_empty,
        "next_run": _calculate_next_run(request.schedule, request.send_time, request.timezone).isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    })
    
    logger.info("scheduled_report_updated", schedule_id=schedule_id)
    return scheduled


@router.post("/scheduled/{schedule_id}/pause")
async def pause_scheduled_report(schedule_id: str):
    """Pause a scheduled report"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    scheduled_reports[schedule_id]["is_active"] = False
    scheduled_reports[schedule_id]["paused_at"] = datetime.utcnow().isoformat()
    
    logger.info("scheduled_report_paused", schedule_id=schedule_id)
    return scheduled_reports[schedule_id]


@router.post("/scheduled/{schedule_id}/resume")
async def resume_scheduled_report(schedule_id: str):
    """Resume a scheduled report"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    scheduled = scheduled_reports[schedule_id]
    scheduled["is_active"] = True
    scheduled["next_run"] = _calculate_next_run(
        ReportSchedule(scheduled["schedule"]),
        scheduled["send_time"],
        scheduled["timezone"]
    ).isoformat()
    
    logger.info("scheduled_report_resumed", schedule_id=schedule_id)
    return scheduled


@router.post("/scheduled/{schedule_id}/run-now")
async def run_scheduled_report_now(schedule_id: str):
    """Trigger immediate run of scheduled report"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    scheduled = scheduled_reports[schedule_id]
    now = datetime.utcnow()
    
    # Generate the report
    report_data = _generate_report_data(
        ReportType(scheduled["report_type"]),
        scheduled.get("parameters", {})
    )
    
    import uuid
    report_id = str(uuid.uuid4())
    
    report = {
        "id": report_id,
        "name": f"{scheduled['name']} - {now.strftime('%Y-%m-%d')}",
        "report_type": scheduled["report_type"],
        "parameters": scheduled.get("parameters", {}),
        "format": scheduled["format"],
        "status": ReportStatus.COMPLETED.value,
        "data": report_data,
        "scheduled_report_id": schedule_id,
        "generated_at": now.isoformat(),
        "tenant_id": scheduled["tenant_id"],
        "created_at": now.isoformat()
    }
    
    reports[report_id] = report
    
    # Update schedule
    scheduled["last_run"] = now.isoformat()
    scheduled["run_count"] = scheduled.get("run_count", 0) + 1
    
    logger.info("scheduled_report_run", schedule_id=schedule_id, report_id=report_id)
    return report


@router.delete("/scheduled/{schedule_id}")
async def delete_scheduled_report(schedule_id: str):
    """Delete a scheduled report"""
    if schedule_id not in scheduled_reports:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    
    del scheduled_reports[schedule_id]
    logger.info("scheduled_report_deleted", schedule_id=schedule_id)
    return {"status": "deleted", "schedule_id": schedule_id}


# Dashboards
@router.post("/dashboards")
async def create_dashboard(
    request: DashboardCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a dashboard"""
    import uuid
    
    dashboard_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    dashboard = {
        "id": dashboard_id,
        "name": request.name,
        "description": request.description,
        "widgets": [w.dict() for w in request.widgets],
        "is_default": request.is_default,
        "shared_with": request.shared_with or [],
        "owner_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    dashboards[dashboard_id] = dashboard
    logger.info("dashboard_created", dashboard_id=dashboard_id, widgets=len(request.widgets))
    return dashboard


@router.get("/dashboards")
async def list_dashboards(
    user_id: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List dashboards"""
    result = [d for d in dashboards.values() if d.get("tenant_id") == tenant_id]
    
    if user_id:
        result = [d for d in result if d.get("owner_id") == user_id or user_id in d.get("shared_with", [])]
    
    return {"dashboards": result, "total": len(result)}


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(dashboard_id: str):
    """Get dashboard with widget data"""
    if dashboard_id not in dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    dashboard = dashboards[dashboard_id]
    
    # Generate data for each widget
    widgets_with_data = []
    for widget in dashboard.get("widgets", []):
        widget_data = _generate_report_data(
            ReportType(widget["report_type"]),
            widget.get("parameters", {})
        )
        widgets_with_data.append({
            **widget,
            "data": widget_data,
            "last_updated": datetime.utcnow().isoformat()
        })
    
    return {
        **dashboard,
        "widgets": widgets_with_data
    }


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: str):
    """Delete a dashboard"""
    if dashboard_id not in dashboards:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    del dashboards[dashboard_id]
    logger.info("dashboard_deleted", dashboard_id=dashboard_id)
    return {"status": "deleted", "dashboard_id": dashboard_id}


@router.get("/types")
async def list_report_types():
    """List available report types"""
    return {
        "report_types": [
            {
                "id": rt.value,
                "name": rt.value.replace("_", " ").title(),
                "description": f"Generate {rt.value.replace('_', ' ')} reports",
                "parameters": ["date_range", "filters", "grouping"]
            }
            for rt in ReportType
        ]
    }


@router.get("/stats")
async def get_reporting_stats(tenant_id: str = Query(default="default")):
    """Get reporting statistics"""
    tenant_reports = [r for r in reports.values() if r.get("tenant_id") == tenant_id]
    tenant_scheduled = [s for s in scheduled_reports.values() if s.get("tenant_id") == tenant_id]
    
    by_type = {}
    for r in tenant_reports:
        rtype = r.get("report_type", "unknown")
        by_type[rtype] = by_type.get(rtype, 0) + 1
    
    return {
        "total_reports": len(tenant_reports),
        "scheduled_reports": len(tenant_scheduled),
        "active_schedules": len([s for s in tenant_scheduled if s.get("is_active")]),
        "by_type": by_type,
        "total_dashboards": len([d for d in dashboards.values() if d.get("tenant_id") == tenant_id])
    }
