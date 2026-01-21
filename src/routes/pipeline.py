"""
Pipeline/Deals API Routes
=========================
Endpoints for managing sales deals and pipeline.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import structlog

from src.pipeline import get_deal_service, DealStage

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


class CreateDealRequest(BaseModel):
    name: str
    amount: float
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    pipeline_id: Optional[str] = None
    close_date: Optional[datetime] = None
    description: str = ""
    source: str = ""
    products: list[str] = []
    tags: list[str] = []


class UpdateDealRequest(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    close_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    source: Optional[str] = None
    products: Optional[list[str]] = None
    competitors: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class MoveStageRequest(BaseModel):
    stage: str
    notes: str = ""


class CloseWonRequest(BaseModel):
    won_reason: str = ""
    notes: str = ""


class CloseLostRequest(BaseModel):
    loss_reason: str = ""
    notes: str = ""


class AddNoteRequest(BaseModel):
    note: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class CreatePipelineRequest(BaseModel):
    name: str
    stages: list[dict]


@router.get("/deals")
async def list_deals(
    stage: Optional[str] = None,
    owner_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    company_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    open_only: bool = False,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    tags: Optional[str] = None,
):
    """List all deals with optional filters."""
    service = get_deal_service()
    
    stage_filter = None
    if stage:
        try:
            stage_filter = DealStage(stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")
    
    tag_list = tags.split(",") if tags else None
    
    deals = service.list_deals(
        stage=stage_filter,
        owner_id=owner_id,
        contact_id=contact_id,
        company_id=company_id,
        pipeline_id=pipeline_id,
        open_only=open_only,
        min_amount=min_amount,
        max_amount=max_amount,
        tags=tag_list,
    )
    
    return {
        "deals": [d.to_dict() for d in deals],
        "total": len(deals),
    }


@router.post("/deals")
async def create_deal(request: CreateDealRequest):
    """Create a new deal."""
    service = get_deal_service()
    
    deal = service.create_deal(
        name=request.name,
        amount=request.amount,
        contact_id=request.contact_id,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        company_id=request.company_id,
        company_name=request.company_name,
        owner_id=request.owner_id,
        owner_name=request.owner_name,
        pipeline_id=request.pipeline_id,
        close_date=request.close_date,
        description=request.description,
        source=request.source,
        products=request.products,
        tags=request.tags,
    )
    
    return {
        "message": "Deal created",
        "deal": deal.to_dict(),
    }


@router.get("/deals/summary")
async def get_pipeline_summary(
    pipeline_id: Optional[str] = None,
    owner_id: Optional[str] = None,
):
    """Get pipeline summary by stage."""
    service = get_deal_service()
    
    return service.get_pipeline_summary(
        pipeline_id=pipeline_id,
        owner_id=owner_id,
    )


@router.get("/deals/forecast")
async def get_forecast(
    months: int = Query(3, ge=1, le=12),
    owner_id: Optional[str] = None,
):
    """Get revenue forecast."""
    service = get_deal_service()
    
    return service.get_forecast(
        months=months,
        owner_id=owner_id,
    )


@router.get("/deals/stats")
async def get_deal_stats(
    owner_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
):
    """Get deal statistics."""
    service = get_deal_service()
    
    return service.get_deal_stats(
        owner_id=owner_id,
        days=days,
    )


@router.get("/stages")
async def list_stages():
    """List available deal stages."""
    return {
        "stages": [
            {"value": s.value, "name": s.name}
            for s in DealStage
        ]
    }


@router.get("/deals/{deal_id}")
async def get_deal(deal_id: str):
    """Get a deal by ID."""
    service = get_deal_service()
    deal = service.get_deal(deal_id)
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {"deal": deal.to_dict()}


@router.put("/deals/{deal_id}")
async def update_deal(deal_id: str, request: UpdateDealRequest):
    """Update a deal."""
    service = get_deal_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    deal = service.update_deal(deal_id, updates)
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "message": "Deal updated",
        "deal": deal.to_dict(),
    }


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: str):
    """Delete a deal."""
    service = get_deal_service()
    
    if not service.delete_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {"message": "Deal deleted"}


@router.post("/deals/{deal_id}/stage")
async def move_stage(deal_id: str, request: MoveStageRequest):
    """Move a deal to a new stage."""
    service = get_deal_service()
    
    try:
        stage = DealStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")
    
    deal = service.move_stage(
        deal_id=deal_id,
        new_stage=stage,
        notes=request.notes,
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "message": "Stage updated",
        "deal": deal.to_dict(),
    }


@router.post("/deals/{deal_id}/won")
async def close_won(deal_id: str, request: CloseWonRequest):
    """Mark a deal as won."""
    service = get_deal_service()
    
    deal = service.close_won(
        deal_id=deal_id,
        won_reason=request.won_reason,
        notes=request.notes,
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "message": "Deal marked as won",
        "deal": deal.to_dict(),
    }


@router.post("/deals/{deal_id}/lost")
async def close_lost(deal_id: str, request: CloseLostRequest):
    """Mark a deal as lost."""
    service = get_deal_service()
    
    deal = service.close_lost(
        deal_id=deal_id,
        loss_reason=request.loss_reason,
        notes=request.notes,
    )
    
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "message": "Deal marked as lost",
        "deal": deal.to_dict(),
    }


@router.get("/deals/{deal_id}/activities")
async def get_activities(
    deal_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Get activities for a deal."""
    service = get_deal_service()
    
    if not service.get_deal(deal_id):
        raise HTTPException(status_code=404, detail="Deal not found")
    
    activities = service.get_activities(deal_id, limit)
    
    return {
        "activities": [a.to_dict() for a in activities],
        "total": len(activities),
    }


@router.post("/deals/{deal_id}/notes")
async def add_note(deal_id: str, request: AddNoteRequest):
    """Add a note to a deal."""
    service = get_deal_service()
    
    activity = service.add_note(
        deal_id=deal_id,
        note=request.note,
        user_id=request.user_id,
        user_name=request.user_name,
    )
    
    if not activity:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    return {
        "message": "Note added",
        "activity": activity.to_dict(),
    }


# Pipeline management
@router.get("/pipelines")
async def list_pipelines(active_only: bool = True):
    """List all pipelines."""
    service = get_deal_service()
    
    pipelines = service.list_pipelines(active_only=active_only)
    
    return {
        "pipelines": [p.to_dict() for p in pipelines],
        "total": len(pipelines),
    }


@router.post("/pipelines")
async def create_pipeline(request: CreatePipelineRequest):
    """Create a new pipeline."""
    service = get_deal_service()
    
    pipeline = service.create_pipeline(
        name=request.name,
        stages=request.stages,
    )
    
    return {
        "message": "Pipeline created",
        "pipeline": pipeline.to_dict(),
    }


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get a pipeline by ID."""
    service = get_deal_service()
    pipeline = service.get_pipeline(pipeline_id)
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return {"pipeline": pipeline.to_dict()}
