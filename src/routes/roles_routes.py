"""
Roles Routes - Role-Based Access Control API
=============================================
REST API endpoints for role and permission management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..roles import (
    RoleService,
    ResourceType,
    Action,
    AccessScope,
    get_role_service,
)


router = APIRouter(prefix="/roles", tags=["Roles"])


# Request/Response models
class CreateRoleRequest(BaseModel):
    """Create role request."""
    name: str
    description: Optional[str] = None
    permissions: Optional[list[dict[str, Any]]] = None
    parent_role_id: Optional[str] = None
    level: int = 0


class UpdateRoleRequest(BaseModel):
    """Update role request."""
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    is_active: Optional[bool] = None


class AddPermissionRequest(BaseModel):
    """Add permission request."""
    resource: str
    action: str
    scope: str = "own"
    conditions: Optional[dict[str, Any]] = None


class AssignRoleRequest(BaseModel):
    """Assign role request."""
    user_id: str
    team_id: Optional[str] = None
    territory_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class RevokeRoleRequest(BaseModel):
    """Revoke role request."""
    user_id: str


class CheckAccessRequest(BaseModel):
    """Check access request."""
    user_id: str
    resource: str
    action: str
    owner_id: Optional[str] = None
    team_id: Optional[str] = None


def get_service() -> RoleService:
    """Get role service instance."""
    return get_role_service()


# Role CRUD
@router.post("")
async def create_role(request: CreateRoleRequest):
    """Create a new role."""
    service = get_service()
    
    role = await service.create_role(
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        parent_role_id=request.parent_role_id,
        level=request.level,
    )
    
    return {
        "id": role.id,
        "name": role.name,
        "level": role.level,
        "permissions_count": len(role.permissions),
    }


@router.get("")
async def list_roles(
    active_only: bool = True,
    include_system: bool = True
):
    """List all roles."""
    service = get_service()
    roles = await service.list_roles(
        active_only=active_only,
        include_system=include_system
    )
    
    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "level": r.level,
                "is_system": r.is_system,
                "is_default": r.is_default,
                "is_active": r.is_active,
                "permissions_count": len(r.permissions),
            }
            for r in roles
        ]
    }


@router.get("/resources")
async def list_resources():
    """List available resource types."""
    return {
        "resources": [
            {"value": r.value, "name": r.name}
            for r in ResourceType
        ]
    }


@router.get("/actions")
async def list_actions():
    """List available actions."""
    return {
        "actions": [
            {"value": a.value, "name": a.name}
            for a in Action
        ]
    }


@router.get("/scopes")
async def list_scopes():
    """List available access scopes."""
    return {
        "scopes": [
            {"value": s.value, "name": s.name}
            for s in AccessScope
        ]
    }


@router.get("/default")
async def get_default_role():
    """Get the default role."""
    service = get_service()
    role = await service.get_default_role()
    
    if not role:
        return {"default_role": None}
    
    return {
        "default_role": {
            "id": role.id,
            "name": role.name,
        }
    }


@router.post("/default/{role_id}")
async def set_default_role(role_id: str):
    """Set a role as the default."""
    service = get_service()
    
    if not await service.set_default_role(role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {"success": True}


@router.get("/{role_id}")
async def get_role(role_id: str):
    """Get a role by ID."""
    service = get_service()
    role = await service.get_role(role_id)
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "level": role.level,
        "parent_role_id": role.parent_role_id,
        "is_system": role.is_system,
        "is_default": role.is_default,
        "is_active": role.is_active,
        "permissions": [
            {
                "id": p.id,
                "resource": p.resource.value,
                "action": p.action.value,
                "scope": p.scope.value,
                "conditions": p.conditions,
            }
            for p in role.permissions
        ],
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
    }


@router.patch("/{role_id}")
async def update_role(role_id: str, request: UpdateRoleRequest):
    """Update a role."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    role = await service.update_role(role_id, updates)
    
    if not role:
        raise HTTPException(status_code=400, detail="Cannot update role (not found or is system role)")
    
    return {"success": True, "role_id": role_id}


@router.delete("/{role_id}")
async def delete_role(role_id: str):
    """Delete a role."""
    service = get_service()
    
    if not await service.delete_role(role_id):
        raise HTTPException(status_code=400, detail="Cannot delete role (not found or is system role)")
    
    return {"success": True}


# Permission management
@router.post("/{role_id}/permissions")
async def add_permission(role_id: str, request: AddPermissionRequest):
    """Add permission to a role."""
    service = get_service()
    
    try:
        resource = ResourceType(request.resource)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    try:
        action = Action(request.action)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    try:
        scope = AccessScope(request.scope)
    except ValueError:
        scope = AccessScope.OWN
    
    permission = await service.add_permission(
        role_id=role_id,
        resource=resource,
        action=action,
        scope=scope,
        conditions=request.conditions,
    )
    
    if not permission:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {
        "id": permission.id,
        "resource": permission.resource.value,
        "action": permission.action.value,
        "scope": permission.scope.value,
    }


@router.delete("/{role_id}/permissions/{permission_id}")
async def remove_permission(role_id: str, permission_id: str):
    """Remove permission from a role."""
    service = get_service()
    
    if not await service.remove_permission(role_id, permission_id):
        raise HTTPException(status_code=404, detail="Role or permission not found")
    
    return {"success": True}


# Role assignment
@router.post("/{role_id}/assign")
async def assign_role(role_id: str, request: AssignRoleRequest):
    """Assign a role to a user."""
    service = get_service()
    
    assignment = await service.assign_role(
        user_id=request.user_id,
        role_id=role_id,
        team_id=request.team_id,
        territory_id=request.territory_id,
        expires_at=request.expires_at,
    )
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {
        "id": assignment.id,
        "user_id": assignment.user_id,
        "role_id": assignment.role_id,
        "assigned_at": assignment.assigned_at.isoformat(),
    }


@router.post("/{role_id}/revoke")
async def revoke_role(role_id: str, request: RevokeRoleRequest):
    """Revoke a role from a user."""
    service = get_service()
    
    if not await service.revoke_role(request.user_id, role_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"success": True}


# User roles and permissions
@router.get("/user/{user_id}/roles")
async def get_user_roles(user_id: str):
    """Get all roles for a user."""
    service = get_service()
    roles = await service.get_user_roles(user_id)
    
    return {
        "user_id": user_id,
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "level": r.level,
            }
            for r in roles
        ]
    }


@router.get("/user/{user_id}/permissions")
async def get_user_permissions(user_id: str):
    """Get all permissions for a user."""
    service = get_service()
    permissions = await service.get_user_permissions(user_id)
    
    return {
        "user_id": user_id,
        "permissions": [
            {
                "id": p.id,
                "resource": p.resource.value,
                "action": p.action.value,
                "scope": p.scope.value,
            }
            for p in permissions
        ]
    }


# Access checking
@router.post("/check-access")
async def check_access(request: CheckAccessRequest):
    """Check if a user has access to a resource."""
    service = get_service()
    
    try:
        resource = ResourceType(request.resource)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    try:
        action = Action(request.action)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    has_access = await service.check_access(
        user_id=request.user_id,
        resource=resource,
        action=action,
        owner_id=request.owner_id,
        team_id=request.team_id,
    )
    
    return {
        "user_id": request.user_id,
        "resource": request.resource,
        "action": request.action,
        "has_access": has_access,
    }


@router.get("/user/{user_id}/scope")
async def get_access_scope(
    user_id: str,
    resource: str,
    action: str
):
    """Get the access scope for a user on a resource."""
    service = get_service()
    
    try:
        resource_enum = ResourceType(resource)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resource type")
    
    try:
        action_enum = Action(action)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    scope = await service.get_accessible_scope(
        user_id=user_id,
        resource=resource_enum,
        action=action_enum
    )
    
    return {
        "user_id": user_id,
        "resource": resource,
        "action": action,
        "scope": scope.value if scope else None,
    }
