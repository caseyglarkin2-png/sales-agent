"""
Territories Routes - Territory Management API
==============================================
REST API for sales territories.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any

from src.territories.territory_service import (
    get_territory_service,
    TerritoryType,
    TerritoryStatus,
    RuleField,
    RuleOperator,
)

router = APIRouter(prefix="/territories", tags=["territories"])


class CreateTerritoryRequest(BaseModel):
    """Request to create a territory."""
    name: str
    description: str
    territory_type: str = "geographic"
    parent_id: Optional[str] = None
    auto_assign: bool = True
    allow_overlap: bool = False
    color: Optional[str] = None
    tags: list[str] = []


class UpdateTerritoryRequest(BaseModel):
    """Request to update a territory."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    auto_assign: Optional[bool] = None
    allow_overlap: Optional[bool] = None
    rule_logic: Optional[str] = None
    color: Optional[str] = None
    tags: Optional[list[str]] = None


class AddRuleRequest(BaseModel):
    """Request to add a rule."""
    field: str
    operator: str
    value: Any
    custom_field_name: Optional[str] = None
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    """Request to update a rule."""
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Any] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class AssignUserRequest(BaseModel):
    """Request to assign a user."""
    user_id: str
    role: str = "owner"
    is_primary: bool = False
    quota: float = 0.0


class UpdateAssignmentRequest(BaseModel):
    """Request to update an assignment."""
    role: Optional[str] = None
    is_primary: Optional[bool] = None
    quota: Optional[float] = None


class NamedAccountRequest(BaseModel):
    """Request for named account operations."""
    company_id: str


class MatchTerritoryRequest(BaseModel):
    """Request to match a territory."""
    company_data: dict[str, Any]


class BulkAssignRequest(BaseModel):
    """Request for bulk assignment."""
    company_ids: list[str]


def territory_to_dict(territory) -> dict:
    """Convert territory to dictionary."""
    return {
        "id": territory.id,
        "name": territory.name,
        "description": territory.description,
        "territory_type": territory.territory_type.value,
        "status": territory.status.value,
        "parent_id": territory.parent_id,
        "level": territory.level,
        "rules": [
            {
                "id": r.id,
                "field": r.field.value,
                "operator": r.operator.value,
                "value": r.value,
                "custom_field_name": r.custom_field_name,
                "priority": r.priority,
                "is_active": r.is_active,
            }
            for r in territory.rules
        ],
        "rule_logic": territory.rule_logic,
        "assignments": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "role": a.role,
                "is_primary": a.is_primary,
                "quota": a.quota,
                "is_active": a.is_active,
            }
            for a in territory.assignments
            if a.is_active
        ],
        "named_account_count": len(territory.named_accounts),
        "excluded_account_count": len(territory.excluded_accounts),
        "primary_owner_id": territory.primary_owner_id,
        "auto_assign": territory.auto_assign,
        "allow_overlap": territory.allow_overlap,
        "color": territory.color,
        "tags": territory.tags,
        "metrics": {
            "account_count": territory.metrics.account_count,
            "deal_count": territory.metrics.deal_count,
            "pipeline_value": territory.metrics.pipeline_value,
            "closed_won": territory.metrics.closed_won,
            "quota": territory.metrics.quota,
            "attainment": territory.metrics.attainment,
        },
        "created_at": territory.created_at.isoformat(),
        "updated_at": territory.updated_at.isoformat(),
    }


@router.post("")
async def create_territory(request: CreateTerritoryRequest):
    """Create a new territory."""
    service = get_territory_service()
    
    territory = await service.create_territory(
        name=request.name,
        description=request.description,
        territory_type=TerritoryType(request.territory_type),
        parent_id=request.parent_id,
        auto_assign=request.auto_assign,
        allow_overlap=request.allow_overlap,
        color=request.color,
        tags=request.tags,
    )
    
    return {"territory": territory_to_dict(territory)}


@router.get("")
async def list_territories(
    territory_type: Optional[str] = None,
    status: Optional[str] = None,
    parent_id: Optional[str] = None,
    owner_id: Optional[str] = None
):
    """List territories with filters."""
    service = get_territory_service()
    
    type_enum = TerritoryType(territory_type) if territory_type else None
    status_enum = TerritoryStatus(status) if status else None
    
    territories = await service.list_territories(
        territory_type=type_enum,
        status=status_enum,
        parent_id=parent_id,
        owner_id=owner_id
    )
    
    return {
        "territories": [territory_to_dict(t) for t in territories],
        "count": len(territories)
    }


@router.get("/export")
async def export_territories():
    """Export all territories."""
    service = get_territory_service()
    
    export_data = await service.export_territories()
    
    return export_data


@router.get("/{territory_id}")
async def get_territory(territory_id: str):
    """Get a territory by ID."""
    service = get_territory_service()
    
    territory = await service.get_territory(territory_id)
    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    return {"territory": territory_to_dict(territory)}


@router.put("/{territory_id}")
async def update_territory(territory_id: str, request: UpdateTerritoryRequest):
    """Update a territory."""
    service = get_territory_service()
    
    updates = request.model_dump(exclude_none=True)
    if "status" in updates:
        updates["status"] = TerritoryStatus(updates["status"])
    
    territory = await service.update_territory(territory_id, updates)
    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    return {"territory": territory_to_dict(territory)}


@router.delete("/{territory_id}")
async def delete_territory(territory_id: str):
    """Delete a territory."""
    service = get_territory_service()
    
    success = await service.delete_territory(territory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    return {"success": True}


@router.get("/{territory_id}/hierarchy")
async def get_territory_hierarchy(territory_id: str):
    """Get territory and all ancestors."""
    service = get_territory_service()
    
    hierarchy = await service.get_territory_hierarchy(territory_id)
    
    return {
        "hierarchy": [territory_to_dict(t) for t in hierarchy]
    }


@router.get("/{territory_id}/children")
async def get_children(territory_id: str):
    """Get child territories."""
    service = get_territory_service()
    
    children = await service.get_children(territory_id)
    
    return {
        "children": [territory_to_dict(t) for t in children],
        "count": len(children)
    }


@router.get("/{territory_id}/stats")
async def get_territory_stats(territory_id: str):
    """Get territory statistics."""
    service = get_territory_service()
    
    stats = await service.get_territory_stats(territory_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    return stats


# Rules
@router.post("/{territory_id}/rules")
async def add_rule(territory_id: str, request: AddRuleRequest):
    """Add a rule to a territory."""
    service = get_territory_service()
    
    rule = await service.add_rule(
        territory_id=territory_id,
        field=RuleField(request.field),
        operator=RuleOperator(request.operator),
        value=request.value,
        custom_field_name=request.custom_field_name,
        priority=request.priority,
    )
    
    if not rule:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


@router.put("/{territory_id}/rules/{rule_id}")
async def update_rule(territory_id: str, rule_id: str, request: UpdateRuleRequest):
    """Update a rule."""
    service = get_territory_service()
    
    updates = request.model_dump(exclude_none=True)
    if "field" in updates:
        updates["field"] = RuleField(updates["field"])
    if "operator" in updates:
        updates["operator"] = RuleOperator(updates["operator"])
    
    rule = await service.update_rule(territory_id, rule_id, updates)
    if not rule:
        raise HTTPException(status_code=404, detail="Territory or rule not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


@router.delete("/{territory_id}/rules/{rule_id}")
async def remove_rule(territory_id: str, rule_id: str):
    """Remove a rule."""
    service = get_territory_service()
    
    success = await service.remove_rule(territory_id, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Territory or rule not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


# Assignments
@router.post("/{territory_id}/assignments")
async def assign_user(territory_id: str, request: AssignUserRequest):
    """Assign a user to a territory."""
    service = get_territory_service()
    
    assignment = await service.assign_user(
        territory_id=territory_id,
        user_id=request.user_id,
        role=request.role,
        is_primary=request.is_primary,
        quota=request.quota,
    )
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


@router.get("/{territory_id}/team")
async def get_territory_team(territory_id: str):
    """Get team members for a territory."""
    service = get_territory_service()
    
    team = await service.get_territory_team(territory_id)
    
    return {"team": team}


@router.put("/assignments/{assignment_id}")
async def update_assignment(assignment_id: str, request: UpdateAssignmentRequest):
    """Update an assignment."""
    service = get_territory_service()
    
    updates = request.model_dump(exclude_none=True)
    assignment = await service.update_assignment(assignment_id, updates)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {
        "assignment": {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "role": assignment.role,
            "is_primary": assignment.is_primary,
            "quota": assignment.quota,
        }
    }


@router.delete("/{territory_id}/assignments/{user_id}")
async def remove_assignment(territory_id: str, user_id: str):
    """Remove a user from a territory."""
    service = get_territory_service()
    
    success = await service.remove_assignment(territory_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"success": True}


@router.get("/user/{user_id}/territories")
async def get_user_territories(user_id: str):
    """Get all territories a user is assigned to."""
    service = get_territory_service()
    
    territories = await service.get_user_territories(user_id)
    
    return {
        "territories": [territory_to_dict(t) for t in territories],
        "count": len(territories)
    }


# Named accounts
@router.post("/{territory_id}/named-accounts")
async def add_named_account(territory_id: str, request: NamedAccountRequest):
    """Add a named account to a territory."""
    service = get_territory_service()
    
    success = await service.add_named_account(territory_id, request.company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


@router.delete("/{territory_id}/named-accounts/{company_id}")
async def remove_named_account(territory_id: str, company_id: str):
    """Remove a named account."""
    service = get_territory_service()
    
    success = await service.remove_named_account(territory_id, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Territory or account not found")
    
    return {"success": True}


@router.get("/{territory_id}/named-accounts")
async def get_named_accounts(territory_id: str):
    """Get named accounts for a territory."""
    service = get_territory_service()
    
    territory = await service.get_territory(territory_id)
    if not territory:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    return {
        "named_accounts": territory.named_accounts,
        "count": len(territory.named_accounts)
    }


@router.post("/{territory_id}/excluded-accounts")
async def add_excluded_account(territory_id: str, request: NamedAccountRequest):
    """Add an excluded account."""
    service = get_territory_service()
    
    success = await service.add_excluded_account(territory_id, request.company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Territory not found")
    
    territory = await service.get_territory(territory_id)
    
    return {"territory": territory_to_dict(territory)}


# Matching
@router.post("/match")
async def match_territory(request: MatchTerritoryRequest):
    """Match a territory for company data."""
    service = get_territory_service()
    
    territory = await service.match_territory(request.company_data)
    
    if not territory:
        return {"territory": None, "matched": False}
    
    return {
        "territory": territory_to_dict(territory),
        "matched": True
    }
