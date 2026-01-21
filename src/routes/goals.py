"""
Goals API Routes
================
Endpoints for managing sales goals and tracking progress.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import structlog

from src.goals import get_goal_service, GoalType, GoalPeriod

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/goals", tags=["Goals"])


class CreateGoalRequest(BaseModel):
    name: str
    goal_type: str
    target_value: float
    period: str = "monthly"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    team_id: Optional[str] = None
    is_team_goal: bool = False


class UpdateGoalRequest(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class UpdateProgressRequest(BaseModel):
    value: float
    notes: str = ""


class IncrementProgressRequest(BaseModel):
    increment: float = 1
    notes: str = ""


class AutoTrackRequest(BaseModel):
    goal_type: str
    value: float = 1
    owner_id: Optional[str] = None


@router.get("")
async def list_goals(
    owner_id: Optional[str] = None,
    team_id: Optional[str] = None,
    goal_type: Optional[str] = None,
    period: Optional[str] = None,
    active_only: bool = True,
):
    """List all goals with optional filters."""
    service = get_goal_service()
    
    # Parse goal type
    type_filter = None
    if goal_type:
        try:
            type_filter = GoalType(goal_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid goal type: {goal_type}")
    
    # Parse period
    period_filter = None
    if period:
        try:
            period_filter = GoalPeriod(period)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid period: {period}")
    
    goals = service.list_goals(
        owner_id=owner_id,
        team_id=team_id,
        goal_type=type_filter,
        period=period_filter,
        active_only=active_only,
    )
    
    return {
        "goals": [g.to_dict() for g in goals],
        "total": len(goals),
    }


@router.post("")
async def create_goal(request: CreateGoalRequest):
    """Create a new goal."""
    service = get_goal_service()
    
    try:
        goal_type = GoalType(request.goal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid goal type: {request.goal_type}")
    
    try:
        period = GoalPeriod(request.period)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid period: {request.period}")
    
    goal = service.create_goal(
        name=request.name,
        goal_type=goal_type,
        target_value=request.target_value,
        period=period,
        start_date=request.start_date,
        end_date=request.end_date,
        owner_id=request.owner_id,
        owner_name=request.owner_name,
        team_id=request.team_id,
        is_team_goal=request.is_team_goal,
    )
    
    logger.info("goal_created_via_api", goal_id=goal.id)
    
    return {
        "message": "Goal created",
        "goal": goal.to_dict(),
    }


@router.get("/dashboard")
async def get_dashboard(
    owner_id: Optional[str] = None,
    team_id: Optional[str] = None,
):
    """Get goal dashboard summary."""
    service = get_goal_service()
    
    return service.get_dashboard(
        owner_id=owner_id,
        team_id=team_id,
    )


@router.get("/leaderboard")
async def get_leaderboard(
    goal_type: Optional[str] = None,
    period: Optional[str] = None,
):
    """Get leaderboard for goals."""
    service = get_goal_service()
    
    # Parse goal type
    type_filter = None
    if goal_type:
        try:
            type_filter = GoalType(goal_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid goal type: {goal_type}")
    
    # Parse period
    period_filter = None
    if period:
        try:
            period_filter = GoalPeriod(period)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid period: {period}")
    
    return {
        "leaderboard": service.get_leaderboard(
            goal_type=type_filter,
            period=period_filter,
        )
    }


@router.get("/types")
async def list_goal_types():
    """List available goal types."""
    return {
        "goal_types": [
            {"value": gt.value, "name": gt.name}
            for gt in GoalType
        ]
    }


@router.get("/periods")
async def list_periods():
    """List available goal periods."""
    return {
        "periods": [
            {"value": p.value, "name": p.name}
            for p in GoalPeriod
        ]
    }


@router.get("/{goal_id}")
async def get_goal(goal_id: str):
    """Get a goal by ID."""
    service = get_goal_service()
    goal = service.get_goal(goal_id)
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {"goal": goal.to_dict()}


@router.put("/{goal_id}")
async def update_goal(goal_id: str, request: UpdateGoalRequest):
    """Update a goal."""
    service = get_goal_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    goal = service.update_goal(goal_id, updates)
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {
        "message": "Goal updated",
        "goal": goal.to_dict(),
    }


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete a goal."""
    service = get_goal_service()
    
    if not service.delete_goal(goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {"message": "Goal deleted"}


@router.post("/{goal_id}/progress")
async def update_progress(goal_id: str, request: UpdateProgressRequest):
    """Update progress on a goal."""
    service = get_goal_service()
    
    progress = service.update_progress(
        goal_id=goal_id,
        new_value=request.value,
        notes=request.notes,
    )
    
    if not progress:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal = service.get_goal(goal_id)
    
    return {
        "message": "Progress updated",
        "progress": progress.to_dict(),
        "goal": goal.to_dict() if goal else None,
    }


@router.post("/{goal_id}/increment")
async def increment_progress(goal_id: str, request: IncrementProgressRequest):
    """Increment progress on a goal."""
    service = get_goal_service()
    
    progress = service.increment_progress(
        goal_id=goal_id,
        increment=request.increment,
        notes=request.notes,
    )
    
    if not progress:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal = service.get_goal(goal_id)
    
    return {
        "message": "Progress incremented",
        "progress": progress.to_dict(),
        "goal": goal.to_dict() if goal else None,
    }


@router.get("/{goal_id}/history")
async def get_progress_history(
    goal_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """Get progress history for a goal."""
    service = get_goal_service()
    
    goal = service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    history = service.get_progress_history(goal_id, limit)
    
    return {
        "goal_id": goal_id,
        "history": [p.to_dict() for p in history],
        "count": len(history),
    }


@router.post("/auto-track")
async def auto_track(request: AutoTrackRequest):
    """Auto-track progress for a goal type."""
    service = get_goal_service()
    
    try:
        goal_type = GoalType(request.goal_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid goal type: {request.goal_type}")
    
    progress = service.auto_track(
        goal_type=goal_type,
        value=request.value,
        owner_id=request.owner_id,
    )
    
    if not progress:
        return {
            "message": "No active goal found for this type",
            "tracked": False,
        }
    
    goal = service.get_goal(progress.goal_id)
    
    return {
        "message": "Progress tracked",
        "tracked": True,
        "progress": progress.to_dict(),
        "goal": goal.to_dict() if goal else None,
    }
