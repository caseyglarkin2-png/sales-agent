"""
Teams Routes - Team Management API
===================================
REST API endpoints for team management, membership, and performance.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..teams import (
    TeamService,
    TeamType,
    TeamRole,
    get_team_service,
)


router = APIRouter(prefix="/teams", tags=["Teams"])


# Request models
class CreateTeamRequest(BaseModel):
    """Create team request."""
    name: str
    type: str
    description: Optional[str] = None
    parent_team_id: Optional[str] = None
    territory_id: Optional[str] = None
    manager_user_id: Optional[str] = None
    quota: Optional[float] = None


class UpdateTeamRequest(BaseModel):
    """Update team request."""
    name: Optional[str] = None
    description: Optional[str] = None
    territory_id: Optional[str] = None
    manager_user_id: Optional[str] = None
    quota: Optional[float] = None
    is_active: Optional[bool] = None


class AddMemberRequest(BaseModel):
    """Add member request."""
    user_id: str
    role: str = "member"
    title: Optional[str] = None
    quota: Optional[float] = None
    commission_rate: Optional[float] = None


class UpdateMemberRequest(BaseModel):
    """Update member request."""
    role: Optional[str] = None
    title: Optional[str] = None
    quota: Optional[float] = None
    commission_rate: Optional[float] = None


class SetGoalRequest(BaseModel):
    """Set goal request."""
    name: str
    target_type: str
    target_value: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class UpdateGoalProgressRequest(BaseModel):
    """Update goal progress request."""
    current_value: float


class RecordPerformanceRequest(BaseModel):
    """Record performance request."""
    period: str
    total_revenue: Optional[float] = 0.0
    total_deals: Optional[int] = 0
    deals_won: Optional[int] = 0
    deals_lost: Optional[int] = 0
    pipeline_value: Optional[float] = 0.0
    activities_count: Optional[int] = 0


def get_service() -> TeamService:
    """Get team service instance."""
    return get_team_service()


# Team CRUD
@router.post("")
async def create_team(request: CreateTeamRequest):
    """Create a new team."""
    service = get_service()
    
    try:
        team_type = TeamType(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team type")
    
    team = await service.create_team(
        name=request.name,
        team_type=team_type,
        description=request.description,
        parent_team_id=request.parent_team_id,
        territory_id=request.territory_id,
        manager_user_id=request.manager_user_id,
        quota=request.quota,
    )
    
    return {
        "id": team.id,
        "name": team.name,
        "type": team.type.value,
    }


@router.get("")
async def list_teams(
    type: Optional[str] = None,
    parent_team_id: Optional[str] = None,
    active_only: bool = True,
):
    """List teams with filters."""
    service = get_service()
    
    team_type = None
    if type:
        try:
            team_type = TeamType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid team type")
    
    teams = await service.list_teams(
        team_type=team_type,
        parent_team_id=parent_team_id,
        active_only=active_only,
    )
    
    return {
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type.value,
                "member_count": len([m for m in t.members if m.is_active]),
                "quota": t.quota,
                "manager_user_id": t.manager_user_id,
            }
            for t in teams
        ]
    }


@router.get("/types")
async def list_team_types():
    """List available team types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in TeamType
        ]
    }


@router.get("/roles")
async def list_team_roles():
    """List available team roles."""
    return {
        "roles": [
            {"value": r.value, "name": r.name}
            for r in TeamRole
        ]
    }


@router.get("/{team_id}")
async def get_team(team_id: str):
    """Get team by ID."""
    service = get_service()
    team = await service.get_team(team_id)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": team.id,
        "name": team.name,
        "type": team.type.value,
        "description": team.description,
        "parent_team_id": team.parent_team_id,
        "territory_id": team.territory_id,
        "manager_user_id": team.manager_user_id,
        "quota": team.quota,
        "is_active": team.is_active,
        "member_count": len([m for m in team.members if m.is_active]),
        "child_teams_count": len(team.child_teams),
        "created_at": team.created_at.isoformat(),
        "updated_at": team.updated_at.isoformat(),
    }


@router.patch("/{team_id}")
async def update_team(team_id: str, request: UpdateTeamRequest):
    """Update team."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    team = await service.update_team(team_id, updates)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {"success": True, "team_id": team_id}


@router.delete("/{team_id}")
async def delete_team(team_id: str):
    """Delete team (soft delete)."""
    service = get_service()
    
    if not await service.delete_team(team_id):
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {"success": True}


@router.get("/{team_id}/hierarchy")
async def get_team_hierarchy(team_id: str):
    """Get team hierarchy (ancestors and descendants)."""
    service = get_service()
    hierarchy = await service.get_team_hierarchy(team_id)
    
    if not hierarchy:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return hierarchy


@router.get("/{team_id}/stats")
async def get_team_stats(team_id: str):
    """Get team statistics."""
    service = get_service()
    stats = await service.get_team_stats(team_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return stats


# Member management
@router.post("/{team_id}/members")
async def add_member(team_id: str, request: AddMemberRequest):
    """Add member to team."""
    service = get_service()
    
    try:
        role = TeamRole(request.role)
    except ValueError:
        role = TeamRole.MEMBER
    
    member = await service.add_member(
        team_id=team_id,
        user_id=request.user_id,
        role=role,
        title=request.title,
        quota=request.quota,
        commission_rate=request.commission_rate,
    )
    
    if not member:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": member.id,
        "team_id": member.team_id,
        "user_id": member.user_id,
        "role": member.role.value,
    }


@router.get("/{team_id}/members")
async def get_team_members(
    team_id: str,
    include_inactive: bool = False
):
    """Get team members."""
    service = get_service()
    members = await service.get_team_members(team_id, include_inactive)
    
    return {
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role.value,
                "title": m.title,
                "quota": m.quota,
                "commission_rate": m.commission_rate,
                "is_active": m.is_active,
                "joined_at": m.joined_at.isoformat(),
            }
            for m in members
        ]
    }


@router.patch("/{team_id}/members/{member_id}")
async def update_member(
    team_id: str,
    member_id: str,
    request: UpdateMemberRequest
):
    """Update team member."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    if "role" in updates:
        try:
            updates["role"] = TeamRole(updates["role"])
        except ValueError:
            del updates["role"]
    
    member = await service.update_member(member_id, updates)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"success": True, "member_id": member_id}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(team_id: str, user_id: str):
    """Remove member from team."""
    service = get_service()
    
    if not await service.remove_member(team_id, user_id):
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"success": True}


@router.post("/{team_id}/members/{user_id}/role")
async def change_member_role(team_id: str, user_id: str, role: str):
    """Change member's role in the team."""
    service = get_service()
    
    try:
        new_role = TeamRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    member = await service.change_member_role(team_id, user_id, new_role)
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"success": True, "new_role": new_role.value}


# User's teams
@router.get("/user/{user_id}/teams")
async def get_user_teams(user_id: str, active_only: bool = True):
    """Get all teams a user belongs to."""
    service = get_service()
    teams = await service.get_user_teams(user_id, active_only)
    
    return {
        "user_id": user_id,
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type.value,
            }
            for t in teams
        ]
    }


# Goals management
@router.post("/{team_id}/goals")
async def set_goal(team_id: str, request: SetGoalRequest):
    """Set a goal for the team."""
    service = get_service()
    
    goal = await service.set_goal(
        team_id=team_id,
        name=request.name,
        target_type=request.target_type,
        target_value=request.target_value,
        period_start=request.period_start,
        period_end=request.period_end,
    )
    
    if not goal:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": goal.id,
        "name": goal.name,
        "target_type": goal.target_type,
        "target_value": goal.target_value,
    }


@router.get("/{team_id}/goals")
async def get_team_goals(team_id: str, active_only: bool = True):
    """Get team goals."""
    service = get_service()
    goals = await service.get_team_goals(team_id, active_only)
    
    return {
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "target_type": g.target_type,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "progress": (g.current_value / g.target_value * 100) if g.target_value > 0 else 0,
                "is_achieved": g.is_achieved,
                "achieved_at": g.achieved_at.isoformat() if g.achieved_at else None,
            }
            for g in goals
        ]
    }


@router.patch("/{team_id}/goals/{goal_id}")
async def update_goal_progress(
    team_id: str,
    goal_id: str,
    request: UpdateGoalProgressRequest
):
    """Update goal progress."""
    service = get_service()
    
    goal = await service.update_goal_progress(goal_id, request.current_value)
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {
        "id": goal.id,
        "current_value": goal.current_value,
        "is_achieved": goal.is_achieved,
    }


# Performance tracking
@router.post("/{team_id}/performance")
async def record_performance(team_id: str, request: RecordPerformanceRequest):
    """Record team performance metrics."""
    service = get_service()
    
    metrics = request.model_dump(exclude={'period'})
    perf = await service.record_performance(
        team_id=team_id,
        period=request.period,
        metrics=metrics
    )
    
    return {
        "team_id": perf.team_id,
        "period": perf.period,
        "recorded": True,
    }


@router.get("/{team_id}/performance/{period}")
async def get_performance(team_id: str, period: str):
    """Get team performance for a period."""
    service = get_service()
    perf = await service.get_performance(team_id, period)
    
    if not perf:
        return {"team_id": team_id, "period": period, "data": None}
    
    return {
        "team_id": perf.team_id,
        "period": perf.period,
        "total_revenue": perf.total_revenue,
        "total_deals": perf.total_deals,
        "deals_won": perf.deals_won,
        "deals_lost": perf.deals_lost,
        "pipeline_value": perf.pipeline_value,
        "win_rate": perf.win_rate,
        "quota_attainment": perf.quota_attainment,
    }


@router.get("/{team_id}/leaderboard")
async def get_leaderboard(
    team_id: str,
    metric: str = "revenue",
    period: Optional[str] = None
):
    """Get team member leaderboard."""
    service = get_service()
    leaderboard = await service.get_leaderboard(team_id, metric, period)
    
    return {
        "team_id": team_id,
        "metric": metric,
        "period": period,
        "leaderboard": leaderboard,
    }
