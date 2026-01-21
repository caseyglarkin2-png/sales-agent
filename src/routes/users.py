"""
User Routes - User and Team API Endpoints
==========================================
REST API for user and team management.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional

from src.users.user_service import (
    get_user_service,
    UserRole,
    UserStatus,
)

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    """Request to create a user."""
    email: str
    first_name: str
    last_name: str
    role: str
    team_id: Optional[str] = None
    manager_id: Optional[str] = None
    title: Optional[str] = None


class UpdateUserRequest(BaseModel):
    """Request to update a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    team_id: Optional[str] = None
    manager_id: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""
    timezone: Optional[str] = None
    locale: Optional[str] = None
    email_notifications: Optional[bool] = None
    browser_notifications: Optional[bool] = None
    daily_digest: Optional[bool] = None
    weekly_report: Optional[bool] = None
    theme: Optional[str] = None


class CreateTeamRequest(BaseModel):
    """Request to create a team."""
    name: str
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None


class UpdateTeamRequest(BaseModel):
    """Request to update a team."""
    name: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    monthly_quota: Optional[float] = None
    quarterly_quota: Optional[float] = None
    annual_quota: Optional[float] = None


class InviteUserRequest(BaseModel):
    """Request to invite a user."""
    email: str
    role: str
    team_id: Optional[str] = None


class AcceptInvitationRequest(BaseModel):
    """Request to accept an invitation."""
    token: str
    first_name: str
    last_name: str


# User endpoints

@router.post("")
async def create_user(request: CreateUserRequest):
    """Create a new user."""
    service = get_user_service()
    
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    
    try:
        user = await service.create_user(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            role=role,
            team_id=request.team_id,
            manager_id=request.manager_id,
            title=request.title
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "created_at": user.created_at.isoformat()
        }
    }


@router.get("")
async def list_users(
    role: Optional[str] = None,
    team_id: Optional[str] = None,
    status: Optional[str] = None,
    manager_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List users with filters."""
    service = get_user_service()
    
    role_enum = UserRole(role) if role else None
    status_enum = UserStatus(status) if status else None
    
    users = await service.list_users(
        role=role_enum,
        team_id=team_id,
        status=status_enum,
        manager_id=manager_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": u.full_name,
                "role": u.role.value,
                "status": u.status.value,
                "title": u.title,
                "team_id": u.team_id,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None
            }
            for u in users
        ],
        "count": len(users)
    }


@router.get("/search")
async def search_users(
    q: str,
    limit: int = Query(default=20, le=50)
):
    """Search users by name or email."""
    service = get_user_service()
    
    users = await service.search_users(query=q, limit=limit)
    
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "team_id": u.team_id
            }
            for u in users
        ],
        "count": len(users)
    }


@router.get("/stats")
async def get_user_stats():
    """Get user and team statistics."""
    service = get_user_service()
    stats = await service.get_stats()
    return stats


@router.get("/roles")
async def list_roles():
    """List available user roles."""
    return {
        "roles": [
            {"value": r.value, "name": r.name}
            for r in UserRole
        ]
    }


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Get a user by ID."""
    service = get_user_service()
    
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "role": user.role.value,
        "status": user.status.value,
        "title": user.title,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "team_id": user.team_id,
        "manager_id": user.manager_id,
        "preferences": {
            "timezone": user.preferences.timezone,
            "locale": user.preferences.locale,
            "email_notifications": user.preferences.email_notifications,
            "theme": user.preferences.theme
        },
        "stats": {
            "contacts_owned": user.contacts_owned,
            "deals_owned": user.deals_owned,
            "emails_sent": user.emails_sent,
            "login_count": user.login_count
        },
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat()
    }


@router.patch("/{user_id}")
async def update_user(user_id: str, request: UpdateUserRequest):
    """Update a user."""
    service = get_user_service()
    
    updates = request.dict(exclude_none=True)
    
    if "role" in updates:
        updates["role"] = UserRole(updates["role"])
    if "status" in updates:
        updates["status"] = UserStatus(updates["status"])
    
    user = await service.update_user(user_id, updates)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "updated_at": user.updated_at.isoformat()
        }
    }


@router.patch("/{user_id}/preferences")
async def update_user_preferences(user_id: str, request: UpdatePreferencesRequest):
    """Update user preferences."""
    service = get_user_service()
    
    user = await service.update_preferences(user_id, request.dict(exclude_none=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "preferences": {
            "timezone": user.preferences.timezone,
            "locale": user.preferences.locale,
            "email_notifications": user.preferences.email_notifications,
            "theme": user.preferences.theme
        }
    }


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user."""
    service = get_user_service()
    
    success = await service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"success": True, "deleted": user_id}


# Team endpoints

@router.post("/teams")
async def create_team(request: CreateTeamRequest):
    """Create a new team."""
    service = get_user_service()
    
    team = await service.create_team(
        name=request.name,
        description=request.description,
        manager_id=request.manager_id,
        parent_team_id=request.parent_team_id
    )
    
    return {
        "success": True,
        "team": {
            "id": team.id,
            "name": team.name,
            "created_at": team.created_at.isoformat()
        }
    }


@router.get("/teams")
async def list_teams(
    parent_team_id: Optional[str] = None,
    manager_id: Optional[str] = None
):
    """List teams."""
    service = get_user_service()
    
    teams = await service.list_teams(
        parent_team_id=parent_team_id,
        manager_id=manager_id
    )
    
    return {
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "manager_id": t.manager_id,
                "member_count": len(t.member_ids),
                "monthly_quota": t.monthly_quota,
                "parent_team_id": t.parent_team_id
            }
            for t in teams
        ],
        "count": len(teams)
    }


@router.get("/teams/{team_id}")
async def get_team(team_id: str):
    """Get a team by ID."""
    service = get_user_service()
    
    team = await service.get_team(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "manager_id": team.manager_id,
        "member_ids": team.member_ids,
        "member_count": len(team.member_ids),
        "parent_team_id": team.parent_team_id,
        "child_team_ids": team.child_team_ids,
        "monthly_quota": team.monthly_quota,
        "quarterly_quota": team.quarterly_quota,
        "annual_quota": team.annual_quota,
        "created_at": team.created_at.isoformat()
    }


@router.get("/teams/{team_id}/members")
async def get_team_members(team_id: str):
    """Get all members of a team."""
    service = get_user_service()
    
    members = await service.get_team_members(team_id)
    
    return {
        "members": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.value,
                "title": u.title
            }
            for u in members
        ],
        "count": len(members)
    }


@router.get("/teams/{team_id}/hierarchy")
async def get_team_hierarchy(team_id: str):
    """Get team hierarchy."""
    service = get_user_service()
    
    result = await service.get_team_hierarchy(team_id)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    
    def serialize_team(t):
        if not t:
            return None
        return {
            "id": t.id,
            "name": t.name,
            "member_count": len(t.member_ids)
        }
    
    return {
        "team": serialize_team(result.get("team")),
        "parent": serialize_team(result.get("parent")),
        "children": [serialize_team(c) for c in result.get("children", [])],
        "members": [
            {"id": u.id, "full_name": u.full_name}
            for u in result.get("members", [])
        ]
    }


@router.patch("/teams/{team_id}")
async def update_team(team_id: str, request: UpdateTeamRequest):
    """Update a team."""
    service = get_user_service()
    
    team = await service.update_team(team_id, request.dict(exclude_none=True))
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "success": True,
        "team": {
            "id": team.id,
            "name": team.name,
            "updated_at": team.updated_at.isoformat()
        }
    }


@router.post("/teams/{team_id}/members/{user_id}")
async def add_user_to_team(team_id: str, user_id: str):
    """Add a user to a team."""
    service = get_user_service()
    
    success = await service.add_user_to_team(user_id, team_id)
    if not success:
        raise HTTPException(status_code=404, detail="User or team not found")
    
    return {"success": True}


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_user_from_team(team_id: str, user_id: str):
    """Remove a user from a team."""
    service = get_user_service()
    
    success = await service.remove_user_from_team(user_id, team_id)
    if not success:
        raise HTTPException(status_code=404, detail="User or team not found")
    
    return {"success": True}


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete a team."""
    service = get_user_service()
    
    success = await service.delete_team(team_id)
    if not success:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {"success": True, "deleted": team_id}


# Invitation endpoints

@router.post("/invitations")
async def invite_user(request: InviteUserRequest):
    """Invite a user."""
    service = get_user_service()
    
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    
    invitation = await service.create_invitation(
        email=request.email,
        role=role,
        invited_by="current_user",  # Would be from auth context
        team_id=request.team_id
    )
    
    return {
        "success": True,
        "invitation": {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role.value,
            "token": invitation.token,
            "expires_at": invitation.expires_at.isoformat()
        }
    }


@router.post("/invitations/accept")
async def accept_invitation(request: AcceptInvitationRequest):
    """Accept an invitation."""
    service = get_user_service()
    
    user = await service.accept_invitation(
        token=request.token,
        first_name=request.first_name,
        last_name=request.last_name
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }
