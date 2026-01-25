"""
Forecasting Routes - Sales Forecasting API
===========================================
REST API for sales forecasts.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

from src.forecasting.forecast_service import (
    get_forecast_service,
    ForecastPeriod,
    ForecastCategory,
    ForecastStatus,
)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


class CreateForecastRequest(BaseModel):
    """Request to create a forecast."""
    name: str
    period: str  # weekly, monthly, quarterly, annual
    year: int
    quarter: Optional[int] = None
    month: Optional[int] = None
    week: Optional[int] = None


class CreateEntryRequest(BaseModel):
    """Request to create a forecast entry."""
    owner_id: str
    quota: float = 0.0
    target: float = 0.0


class UpdateEntryRequest(BaseModel):
    """Request to update an entry."""
    quota: Optional[float] = None
    target: Optional[float] = None
    notes: Optional[str] = None


class AddDealRequest(BaseModel):
    """Request to add a deal to forecast."""
    deal_id: str
    deal_name: str
    amount: float
    probability: float
    expected_close_date: str  # ISO format
    stage: str
    category: str = "pipeline"
    owner_id: Optional[str] = None
    company_id: Optional[str] = None
    product_line: Optional[str] = None


class UpdateDealCategoryRequest(BaseModel):
    """Request to update deal category."""
    deal_id: str
    category: str


class PushDealRequest(BaseModel):
    """Request to push a deal."""
    deal_id: str
    new_close_date: str  # ISO format


class AddAdjustmentRequest(BaseModel):
    """Request to add an adjustment."""
    deal_id: Optional[str] = None
    original_amount: float
    adjusted_amount: float
    reason: str
    adjusted_by: str


class ApproveRequest(BaseModel):
    """Request to approve forecast."""
    approver_id: str


class SetQuotaRequest(BaseModel):
    """Request to set quota."""
    owner_id: str
    period_key: str
    quota: float


def forecast_to_dict(forecast) -> dict:
    """Convert forecast to dictionary."""
    return {
        "id": forecast.id,
        "name": forecast.name,
        "period": forecast.period.value,
        "year": forecast.year,
        "quarter": forecast.quarter,
        "month": forecast.month,
        "week": forecast.week,
        "status": forecast.status.value,
        "total_quota": forecast.total_quota,
        "total_closed_won": forecast.total_closed_won,
        "total_pipeline": forecast.total_pipeline,
        "total_commit": forecast.total_commit,
        "total_best_case": forecast.total_best_case,
        "entry_count": len(forecast.entries),
        "locked_at": forecast.locked_at.isoformat() if forecast.locked_at else None,
        "created_at": forecast.created_at.isoformat(),
        "updated_at": forecast.updated_at.isoformat(),
    }


def entry_to_dict(entry) -> dict:
    """Convert entry to dictionary."""
    return {
        "id": entry.id,
        "period": entry.period.value,
        "period_start": entry.period_start.isoformat(),
        "period_end": entry.period_end.isoformat(),
        "owner_id": entry.owner_id,
        "quota": entry.quota,
        "target": entry.target,
        "pipeline_total": entry.pipeline_total,
        "commit_amount": entry.commit_amount,
        "best_case_amount": entry.best_case_amount,
        "weighted_amount": entry.weighted_amount,
        "closed_won": entry.closed_won,
        "closed_lost": entry.closed_lost,
        "attainment_percentage": entry.attainment_percentage,
        "gap_to_quota": entry.gap_to_quota,
        "coverage_ratio": entry.coverage_ratio,
        "deal_count": len(entry.deals),
        "status": entry.status.value,
        "notes": entry.notes,
        "submitted_at": entry.submitted_at.isoformat() if entry.submitted_at else None,
        "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        "approved_by": entry.approved_by,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def deal_to_dict(deal) -> dict:
    """Convert deal forecast to dictionary."""
    return {
        "deal_id": deal.deal_id,
        "deal_name": deal.deal_name,
        "amount": deal.amount,
        "probability": deal.probability,
        "expected_close_date": deal.expected_close_date.isoformat(),
        "category": deal.category.value,
        "stage": deal.stage,
        "stage_category": deal.stage_category.value,
        "weighted_amount": deal.weighted_amount,
        "owner_id": deal.owner_id,
        "company_id": deal.company_id,
        "product_line": deal.product_line,
        "is_pushed": deal.is_pushed,
        "push_count": deal.push_count,
    }


@router.post("")
async def create_forecast(request: CreateForecastRequest):
    """Create a new forecast."""
    service = get_forecast_service()
    
    forecast = await service.create_forecast(
        name=request.name,
        period=ForecastPeriod(request.period),
        year=request.year,
        quarter=request.quarter,
        month=request.month,
        week=request.week,
    )
    
    return {"forecast": forecast_to_dict(forecast)}


@router.get("")
async def list_forecasts(
    period: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None
):
    """List forecasts with filters."""
    service = get_forecast_service()
    
    period_enum = ForecastPeriod(period) if period else None
    status_enum = ForecastStatus(status) if status else None
    
    forecasts = await service.list_forecasts(
        period=period_enum,
        year=year,
        status=status_enum
    )
    
    return {
        "forecasts": [forecast_to_dict(f) for f in forecasts],
        "count": len(forecasts)
    }


@router.get("/{forecast_id}")
async def get_forecast(forecast_id: str):
    """Get a forecast by ID."""
    service = get_forecast_service()
    
    forecast = await service.get_forecast(forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return {"forecast": forecast_to_dict(forecast)}


@router.get("/{forecast_id}/summary")
async def get_forecast_summary(forecast_id: str):
    """Get forecast summary."""
    service = get_forecast_service()
    
    summary = await service.get_forecast_summary(forecast_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return summary


@router.get("/{forecast_id}/team")
async def get_team_forecast(forecast_id: str):
    """Get team forecast breakdown."""
    service = get_forecast_service()
    
    team = await service.get_team_forecast(forecast_id)
    
    return {"team": team}


@router.post("/{forecast_id}/lock")
async def lock_forecast(forecast_id: str):
    """Lock a forecast."""
    service = get_forecast_service()
    
    success = await service.lock_forecast(forecast_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot lock forecast")
    
    forecast = await service.get_forecast(forecast_id)
    
    return {"forecast": forecast_to_dict(forecast)}


# Entries
@router.post("/{forecast_id}/entries")
async def create_entry(forecast_id: str, request: CreateEntryRequest):
    """Create a forecast entry."""
    service = get_forecast_service()
    
    entry = await service.create_entry(
        forecast_id=forecast_id,
        owner_id=request.owner_id,
        quota=request.quota,
        target=request.target,
    )
    
    if not entry:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return {"entry": entry_to_dict(entry)}


@router.get("/{forecast_id}/entries")
async def list_entries(forecast_id: str):
    """List entries for a forecast."""
    service = get_forecast_service()
    
    forecast = await service.get_forecast(forecast_id)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    return {
        "entries": [entry_to_dict(e) for e in forecast.entries],
        "count": len(forecast.entries)
    }


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    """Get a forecast entry."""
    service = get_forecast_service()
    
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"entry": entry_to_dict(entry)}


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, request: UpdateEntryRequest):
    """Update a forecast entry."""
    service = get_forecast_service()
    
    updates = request.model_dump(exclude_none=True)
    entry = await service.update_entry(entry_id, updates)
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"entry": entry_to_dict(entry)}


@router.get("/entries/{entry_id}/deals")
async def get_entry_deals(entry_id: str):
    """Get deals for an entry."""
    service = get_forecast_service()
    
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {
        "deals": [deal_to_dict(d) for d in entry.deals],
        "count": len(entry.deals)
    }


@router.post("/entries/{entry_id}/deals")
async def add_deal_to_entry(entry_id: str, request: AddDealRequest):
    """Add a deal to a forecast entry."""
    service = get_forecast_service()
    
    deal = await service.add_deal_to_forecast(
        entry_id=entry_id,
        deal_id=request.deal_id,
        deal_name=request.deal_name,
        amount=request.amount,
        probability=request.probability,
        expected_close_date=datetime.fromisoformat(request.expected_close_date),
        stage=request.stage,
        category=ForecastCategory(request.category),
        owner_id=request.owner_id,
        company_id=request.company_id,
        product_line=request.product_line,
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry = await service.get_entry(entry_id)
    
    return {"entry": entry_to_dict(entry)}


@router.put("/entries/{entry_id}/deals/category")
async def update_deal_category(entry_id: str, request: UpdateDealCategoryRequest):
    """Update deal forecast category."""
    service = get_forecast_service()
    
    success = await service.update_deal_category(
        entry_id=entry_id,
        deal_id=request.deal_id,
        category=ForecastCategory(request.category)
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Entry or deal not found")
    
    entry = await service.get_entry(entry_id)
    
    return {"entry": entry_to_dict(entry)}


@router.post("/entries/{entry_id}/deals/push")
async def push_deal(entry_id: str, request: PushDealRequest):
    """Mark a deal as pushed."""
    service = get_forecast_service()
    
    success = await service.push_deal(
        entry_id=entry_id,
        deal_id=request.deal_id,
        new_close_date=datetime.fromisoformat(request.new_close_date)
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Entry or deal not found")
    
    entry = await service.get_entry(entry_id)
    
    return {"entry": entry_to_dict(entry)}


@router.get("/entries/{entry_id}/pushed-deals")
async def get_pushed_deals(entry_id: str):
    """Get pushed deals for an entry."""
    service = get_forecast_service()
    
    deals = await service.get_pushed_deals(entry_id)
    
    return {
        "deals": [deal_to_dict(d) for d in deals],
        "count": len(deals)
    }


@router.get("/entries/{entry_id}/category-breakdown")
async def get_category_breakdown(entry_id: str):
    """Get deal category breakdown."""
    service = get_forecast_service()
    
    breakdown = await service.get_category_breakdown(entry_id)
    
    return breakdown


@router.get("/entries/{entry_id}/stage-breakdown")
async def get_stage_breakdown(entry_id: str):
    """Get deal stage breakdown."""
    service = get_forecast_service()
    
    breakdown = await service.get_stage_breakdown(entry_id)
    
    return {"stages": breakdown}


# Adjustments
@router.post("/entries/{entry_id}/adjustments")
async def add_adjustment(entry_id: str, request: AddAdjustmentRequest):
    """Add a forecast adjustment."""
    service = get_forecast_service()
    
    adjustment = await service.add_adjustment(
        entry_id=entry_id,
        deal_id=request.deal_id,
        original_amount=request.original_amount,
        adjusted_amount=request.adjusted_amount,
        reason=request.reason,
        adjusted_by=request.adjusted_by,
    )
    
    if not adjustment:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {
        "adjustment": {
            "id": adjustment.id,
            "original_amount": adjustment.original_amount,
            "adjusted_amount": adjustment.adjusted_amount,
            "reason": adjustment.reason,
        }
    }


@router.get("/entries/{entry_id}/adjustments")
async def get_adjustments(entry_id: str):
    """Get adjustments for an entry."""
    service = get_forecast_service()
    
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {
        "adjustments": [
            {
                "id": a.id,
                "deal_id": a.deal_id,
                "original_amount": a.original_amount,
                "adjusted_amount": a.adjusted_amount,
                "reason": a.reason,
                "adjusted_by": a.adjusted_by,
                "adjusted_at": a.adjusted_at.isoformat(),
            }
            for a in entry.adjustments
        ]
    }


# Workflow
@router.post("/entries/{entry_id}/submit")
async def submit_forecast(entry_id: str):
    """Submit forecast for approval."""
    service = get_forecast_service()
    
    success = await service.submit_forecast(entry_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot submit forecast")
    
    entry = await service.get_entry(entry_id)
    
    return {"entry": entry_to_dict(entry)}


@router.post("/entries/{entry_id}/approve")
async def approve_forecast(entry_id: str, request: ApproveRequest):
    """Approve a forecast entry."""
    service = get_forecast_service()
    
    success = await service.approve_forecast(entry_id, request.approver_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve forecast")
    
    entry = await service.get_entry(entry_id)
    
    return {"entry": entry_to_dict(entry)}


# Quotas
@router.post("/quotas")
async def set_quota(request: SetQuotaRequest):
    """Set quota for an owner."""
    service = get_forecast_service()
    
    await service.set_quota(
        owner_id=request.owner_id,
        period_key=request.period_key,
        quota=request.quota
    )
    
    return {"success": True}


@router.get("/quotas/{owner_id}")
async def get_quota(owner_id: str, period_key: str = Query(...)):
    """Get quota for an owner."""
    service = get_forecast_service()
    
    quota = await service.get_quota(owner_id, period_key)
    
    return {
        "owner_id": owner_id,
        "period_key": period_key,
        "quota": quota
    }


# Analytics
@router.get("/trend")
async def get_forecast_trend(
    owner_id: Optional[str] = None,
    periods: int = Query(default=4, le=12)
):
    """Get forecast trend over periods."""
    service = get_forecast_service()
    
    trend = await service.get_forecast_trend(
        owner_id=owner_id,
        periods=periods
    )
    
    return {"trend": trend}


@router.get("/entries/{entry_id}/ai-prediction")
async def get_ai_prediction(entry_id: str):
    """Get AI-powered forecast prediction."""
    service = get_forecast_service()
    
    prediction = await service.generate_ai_forecast(entry_id)
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return prediction
