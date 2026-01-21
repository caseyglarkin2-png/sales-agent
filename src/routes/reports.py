"""
Reporting Routes.

API endpoints for report generation and retrieval.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from src.reporting import get_reporting_engine, ReportType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/types")
async def get_types() -> Dict[str, Any]:
    """Get available report types."""
    return {
        "types": [
            {"id": t.value, "name": t.value.replace("_", " ").title()}
            for t in ReportType
        ],
    }


@router.get("/")
async def list_reports(
    report_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """List generated reports."""
    engine = get_reporting_engine()
    
    type_filter = None
    if report_type:
        try:
            type_filter = ReportType(report_type)
        except ValueError:
            pass
    
    reports = engine.list_reports(report_type=type_filter, limit=limit)
    
    return {
        "reports": reports,
        "count": len(reports),
    }


@router.post("/daily")
async def generate_daily_report(
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate daily report."""
    engine = get_reporting_engine()
    
    report_date = None
    if date:
        try:
            report_date = datetime.fromisoformat(date)
        except ValueError:
            pass
    
    report = await engine.generate_daily_report(date=report_date)
    
    return {
        "status": "success",
        "report": report.to_dict(),
    }


@router.post("/weekly")
async def generate_weekly_report(
    week_start: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate weekly report."""
    engine = get_reporting_engine()
    
    start_date = None
    if week_start:
        try:
            start_date = datetime.fromisoformat(week_start)
        except ValueError:
            pass
    
    report = await engine.generate_weekly_report(week_start=start_date)
    
    return {
        "status": "success",
        "report": report.to_dict(),
    }


@router.post("/campaign/{campaign_id}")
async def generate_campaign_report(campaign_id: str) -> Dict[str, Any]:
    """Generate campaign report."""
    engine = get_reporting_engine()
    
    report = await engine.generate_campaign_report(campaign_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "status": "success",
        "report": report.to_dict(),
    }


@router.get("/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """Get a report by ID."""
    engine = get_reporting_engine()
    report = engine.get_report(report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "report": report,
    }


@router.get("/{report_id}/markdown")
async def get_report_markdown(report_id: str):
    """Get report in markdown format."""
    engine = get_reporting_engine()
    markdown = engine.get_report_markdown(report_id)
    
    if not markdown:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return PlainTextResponse(content=markdown, media_type="text/markdown")
