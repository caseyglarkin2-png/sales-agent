"""
Quota Routes - Quota Management API
====================================
REST API endpoints for quota management and tracking.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import date

from ..quotas import (
    QuotaService,
    get_quota_service,
)
from ..quotas.quota_service import (
    QuotaType,
    QuotaPeriod,
    QuotaStatus,
    AttainmentStatus,
)


router = APIRouter(prefix="/quotas", tags=["Quotas"])


# Request models
class CreateQuotaRequest(BaseModel):
    """Create quota request."""
    name: str
    quota_type: str
    period: str
    target: float
    currency: str = "USD"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    parent_quota_id: Optional[str] = None


class UpdateQuotaRequest(BaseModel):
    """Update quota request."""
    name: Optional[str] = None
    target: Optional[float] = None
    status: Optional[str] = None
    description: Optional[str] = None


class AssignQuotaRequest(BaseModel):
    """Assign quota request."""
    assignee_type: str  # "user" or "team"
    assignee_id: str
    target: Optional[float] = None
    weight: float = 1.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class RecordAttainmentRequest(BaseModel):
    """Record attainment request."""
    period_start: date
    period_end: date
    actual: float
    deals_count: int = 0
    pipeline_value: float = 0.0
    forecast_value: float = 0.0


class DistributeQuotaRequest(BaseModel):
    """Distribute quota request."""
    assignee_ids: list[str]
    assignee_type: str = "user"
    distribution: str = "equal"  # "equal", "weighted", "custom"
    custom_targets: Optional[dict[str, float]] = None


def get_service() -> QuotaService:
    """Get quota service instance."""
    return get_quota_service()


# Enums
@router.get("/types")
async def list_quota_types():
    """List quota types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in QuotaType
        ]
    }


@router.get("/periods")
async def list_periods():
    """List quota periods."""
    return {
        "periods": [
            {"value": p.value, "name": p.name}
            for p in QuotaPeriod
        ]
    }


@router.get("/statuses")
async def list_statuses():
    """List quota statuses."""
    return {
        "statuses": [
            {"value": s.value, "name": s.name}
            for s in QuotaStatus
        ]
    }


# Quota CRUD
@router.post("")
async def create_quota(
    request: CreateQuotaRequest,
    org_id: str,
    user_id: Optional[str] = None,
):
    """Create a new quota."""
    service = get_service()
    
    try:
        quota_type = QuotaType(request.quota_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid quota type")
    
    try:
        period = QuotaPeriod(request.period)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    quota = await service.create_quota(
        name=request.name,
        quota_type=quota_type,
        period=period,
        target=request.target,
        org_id=org_id,
        currency=request.currency,
        start_date=request.start_date,
        end_date=request.end_date,
        description=request.description,
        parent_quota_id=request.parent_quota_id,
        created_by=user_id,
    )
    
    return {
        "id": quota.id,
        "name": quota.name,
        "quota_type": quota.quota_type.value,
        "period": quota.period.value,
        "target": quota.target,
        "status": quota.status.value,
        "created_at": quota.created_at.isoformat(),
    }


@router.get("")
async def list_quotas(
    org_id: str,
    quota_type: Optional[str] = None,
    period: Optional[str] = None,
    status: Optional[str] = None,
):
    """List quotas."""
    service = get_service()
    
    qt = None
    if quota_type:
        try:
            qt = QuotaType(quota_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid quota type")
    
    p = None
    if period:
        try:
            p = QuotaPeriod(period)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid period")
    
    s = None
    if status:
        try:
            s = QuotaStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    quotas = await service.list_quotas(org_id, qt, p, s)
    
    return {
        "quotas": [
            {
                "id": q.id,
                "name": q.name,
                "quota_type": q.quota_type.value,
                "period": q.period.value,
                "target": q.target,
                "currency": q.currency,
                "status": q.status.value,
                "start_date": q.start_date.isoformat() if q.start_date else None,
                "end_date": q.end_date.isoformat() if q.end_date else None,
            }
            for q in quotas
        ]
    }


@router.get("/{quota_id}")
async def get_quota(quota_id: str):
    """Get a quota by ID."""
    service = get_service()
    quota = await service.get_quota(quota_id)
    
    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")
    
    return {
        "id": quota.id,
        "name": quota.name,
        "quota_type": quota.quota_type.value,
        "period": quota.period.value,
        "target": quota.target,
        "currency": quota.currency,
        "status": quota.status.value,
        "description": quota.description,
        "start_date": quota.start_date.isoformat() if quota.start_date else None,
        "end_date": quota.end_date.isoformat() if quota.end_date else None,
        "parent_quota_id": quota.parent_quota_id,
        "created_at": quota.created_at.isoformat(),
        "updated_at": quota.updated_at.isoformat(),
        "created_by": quota.created_by,
    }


@router.patch("/{quota_id}")
async def update_quota(
    quota_id: str,
    request: UpdateQuotaRequest,
    user_id: Optional[str] = None,
):
    """Update a quota."""
    service = get_service()
    
    status = None
    if request.status:
        try:
            status = QuotaStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    quota = await service.update_quota(
        quota_id=quota_id,
        name=request.name,
        target=request.target,
        status=status,
        description=request.description,
        updated_by=user_id,
    )
    
    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")
    
    return {"success": True, "updated_at": quota.updated_at.isoformat()}


@router.delete("/{quota_id}")
async def delete_quota(quota_id: str):
    """Delete a quota."""
    service = get_service()
    
    if not await service.delete_quota(quota_id):
        raise HTTPException(status_code=404, detail="Quota not found")
    
    return {"success": True}


# Assignments
@router.post("/{quota_id}/assignments")
async def assign_quota(quota_id: str, request: AssignQuotaRequest):
    """Assign a quota to a user or team."""
    service = get_service()
    
    assignment = await service.assign_quota(
        quota_id=quota_id,
        assignee_type=request.assignee_type,
        assignee_id=request.assignee_id,
        target=request.target,
        weight=request.weight,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Quota not found")
    
    return {
        "id": assignment.id,
        "quota_id": assignment.quota_id,
        "assignee_type": assignment.assignee_type,
        "assignee_id": assignment.assignee_id,
        "target": assignment.target,
    }


@router.get("/{quota_id}/assignments")
async def list_quota_assignments(quota_id: str):
    """List assignments for a quota."""
    service = get_service()
    assignments = await service.list_assignments(quota_id=quota_id)
    
    return {
        "assignments": [
            {
                "id": a.id,
                "assignee_type": a.assignee_type,
                "assignee_id": a.assignee_id,
                "target": a.target,
                "status": a.status.value,
            }
            for a in assignments
        ]
    }


@router.post("/{quota_id}/distribute")
async def distribute_quota(quota_id: str, request: DistributeQuotaRequest):
    """Distribute quota among multiple assignees."""
    service = get_service()
    
    assignments = await service.distribute_quota(
        quota_id=quota_id,
        assignee_ids=request.assignee_ids,
        assignee_type=request.assignee_type,
        distribution=request.distribution,
        custom_targets=request.custom_targets,
    )
    
    return {
        "assignments": [
            {
                "id": a.id,
                "assignee_id": a.assignee_id,
                "target": a.target,
            }
            for a in assignments
        ],
        "count": len(assignments),
    }


@router.get("/assignments/{assignment_id}")
async def get_assignment(assignment_id: str):
    """Get an assignment by ID."""
    service = get_service()
    assignment = await service.get_assignment(assignment_id)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {
        "id": assignment.id,
        "quota_id": assignment.quota_id,
        "assignee_type": assignment.assignee_type,
        "assignee_id": assignment.assignee_id,
        "target": assignment.target,
        "weight": assignment.weight,
        "status": assignment.status.value,
        "start_date": assignment.start_date.isoformat() if assignment.start_date else None,
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
    }


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str):
    """Delete an assignment."""
    service = get_service()
    
    if not await service.delete_assignment(assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"success": True}


# Attainment
@router.post("/assignments/{assignment_id}/attainment")
async def record_attainment(assignment_id: str, request: RecordAttainmentRequest):
    """Record quota attainment."""
    service = get_service()
    
    attainment = await service.record_attainment(
        assignment_id=assignment_id,
        period_start=request.period_start,
        period_end=request.period_end,
        actual=request.actual,
        deals_count=request.deals_count,
        pipeline_value=request.pipeline_value,
        forecast_value=request.forecast_value,
    )
    
    if not attainment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {
        "id": attainment.id,
        "target": attainment.target,
        "actual": attainment.actual,
        "attainment_percent": attainment.attainment_percent,
        "gap": attainment.gap,
        "status": attainment.status.value,
    }


@router.get("/assignments/{assignment_id}/attainment")
async def get_attainment(assignment_id: str):
    """Get attainment for an assignment."""
    service = get_service()
    attainment = await service.get_attainment(assignment_id)
    
    if not attainment:
        return {"attainment": None}
    
    return {
        "id": attainment.id,
        "period_start": attainment.period_start.isoformat(),
        "period_end": attainment.period_end.isoformat(),
        "target": attainment.target,
        "actual": attainment.actual,
        "attainment_percent": attainment.attainment_percent,
        "gap": attainment.gap,
        "status": attainment.status.value,
        "deals_count": attainment.deals_count,
        "pipeline_value": attainment.pipeline_value,
        "forecast_value": attainment.forecast_value,
    }


# Summaries
@router.get("/users/{user_id}/summary")
async def get_user_quota_summary(user_id: str, org_id: str):
    """Get quota summary for a user."""
    service = get_service()
    return await service.get_user_quota_summary(user_id, org_id)


@router.get("/teams/{team_id}/summary")
async def get_team_quota_summary(team_id: str, org_id: str):
    """Get quota summary for a team."""
    service = get_service()
    return await service.get_team_quota_summary(team_id, org_id)


# Leaderboard
@router.get("/leaderboard")
async def get_leaderboard(
    org_id: str,
    quota_type: Optional[str] = None,
):
    """Get quota attainment leaderboard."""
    service = get_service()
    
    qt = None
    if quota_type:
        try:
            qt = QuotaType(quota_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid quota type")
    
    return {"leaderboard": await service.get_leaderboard(org_id, qt)}


# History
@router.get("/{quota_id}/history")
async def get_quota_history(quota_id: str):
    """Get quota change history."""
    service = get_service()
    history = await service.get_quota_history(quota_id)
    
    return {
        "history": [
            {
                "id": h.id,
                "change_type": h.change_type,
                "changed_by": h.changed_by,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "changed_at": h.changed_at.isoformat(),
            }
            for h in history
        ]
    }
