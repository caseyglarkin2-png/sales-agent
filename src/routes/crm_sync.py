"""
CRM Sync API Routes
===================
Endpoints for managing CRM synchronization.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Optional
import structlog

from src.crm_sync import (
    get_crm_sync_engine,
    SyncDirection,
    ConflictResolution,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/crm-sync", tags=["CRM Sync"])


class CreateConfigRequest(BaseModel):
    name: str
    crm_type: str
    object_type: str
    direction: str = "bidirectional"
    conflict_resolution: str = "newest_wins"
    sync_interval_minutes: int = 15


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    direction: Optional[str] = None
    conflict_resolution: Optional[str] = None
    sync_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class AddFieldMappingRequest(BaseModel):
    local_field: str
    crm_field: str
    direction: str = "bidirectional"
    is_required: bool = False
    default_value: Any = None


class SyncRequest(BaseModel):
    local_records: list[dict] = None
    crm_records: list[dict] = None


@router.get("/configs")
async def list_configs(
    crm_type: Optional[str] = None,
    object_type: Optional[str] = None,
    active_only: bool = True,
):
    """List all sync configurations."""
    engine = get_crm_sync_engine()
    configs = engine.list_configs(
        crm_type=crm_type,
        object_type=object_type,
        active_only=active_only,
    )
    
    return {
        "configs": [c.to_dict() for c in configs],
        "total": len(configs),
    }


@router.post("/configs")
async def create_config(request: CreateConfigRequest):
    """Create a new sync configuration."""
    engine = get_crm_sync_engine()
    
    try:
        direction = SyncDirection(request.direction)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid direction: {request.direction}")
    
    try:
        conflict_res = ConflictResolution(request.conflict_resolution)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid conflict resolution: {request.conflict_resolution}")
    
    config = engine.create_config(
        name=request.name,
        crm_type=request.crm_type,
        object_type=request.object_type,
        direction=direction,
        conflict_resolution=conflict_res,
        sync_interval_minutes=request.sync_interval_minutes,
    )
    
    return {
        "message": "Config created",
        "config": config.to_dict(),
    }


@router.get("/configs/{config_id}")
async def get_config(config_id: str):
    """Get a sync configuration by ID."""
    engine = get_crm_sync_engine()
    config = engine.get_config(config_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {"config": config.to_dict()}


@router.put("/configs/{config_id}")
async def update_config(config_id: str, request: UpdateConfigRequest):
    """Update a sync configuration."""
    engine = get_crm_sync_engine()
    
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.direction is not None:
        try:
            updates["direction"] = SyncDirection(request.direction)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {request.direction}")
    if request.conflict_resolution is not None:
        try:
            updates["conflict_resolution"] = ConflictResolution(request.conflict_resolution)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid conflict resolution: {request.conflict_resolution}")
    if request.sync_interval_minutes is not None:
        updates["sync_interval_minutes"] = request.sync_interval_minutes
    if request.is_active is not None:
        updates["is_active"] = request.is_active
    
    config = engine.update_config(config_id, updates)
    
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {
        "message": "Config updated",
        "config": config.to_dict(),
    }


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    """Delete a sync configuration."""
    engine = get_crm_sync_engine()
    
    if not engine.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {"message": "Config deleted"}


@router.post("/configs/{config_id}/mappings")
async def add_field_mapping(config_id: str, request: AddFieldMappingRequest):
    """Add a field mapping to a configuration."""
    engine = get_crm_sync_engine()
    
    try:
        direction = SyncDirection(request.direction)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid direction: {request.direction}")
    
    mapping = engine.add_field_mapping(
        config_id=config_id,
        local_field=request.local_field,
        crm_field=request.crm_field,
        direction=direction,
        is_required=request.is_required,
        default_value=request.default_value,
    )
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {
        "message": "Mapping added",
        "mapping": mapping.to_dict(),
    }


@router.delete("/configs/{config_id}/mappings/{local_field}")
async def remove_field_mapping(config_id: str, local_field: str):
    """Remove a field mapping from a configuration."""
    engine = get_crm_sync_engine()
    
    if not engine.remove_field_mapping(config_id, local_field):
        raise HTTPException(status_code=404, detail="Config or mapping not found")
    
    return {"message": "Mapping removed"}


@router.post("/configs/{config_id}/sync")
async def run_sync(config_id: str, request: SyncRequest):
    """Run a sync operation."""
    engine = get_crm_sync_engine()
    
    result = engine.sync(
        config_id=config_id,
        local_records=request.local_records,
        crm_records=request.crm_records,
    )
    
    return {
        "message": "Sync completed",
        "result": result.to_dict(),
    }


@router.get("/history")
async def get_sync_history(
    config_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Get sync history."""
    engine = get_crm_sync_engine()
    
    history = engine.get_sync_history(
        config_id=config_id,
        limit=limit,
    )
    
    return {
        "history": [h.to_dict() for h in history],
        "total": len(history),
    }


@router.get("/pending")
async def get_pending_syncs():
    """Get configs that need to be synced."""
    engine = get_crm_sync_engine()
    
    pending = engine.get_pending_syncs()
    
    return {
        "pending": [c.to_dict() for c in pending],
        "total": len(pending),
    }


@router.get("/stats")
async def get_sync_stats():
    """Get overall sync statistics."""
    engine = get_crm_sync_engine()
    
    return engine.get_sync_stats()


@router.get("/directions")
async def list_directions():
    """List available sync directions."""
    return {
        "directions": [
            {"value": d.value, "name": d.name}
            for d in SyncDirection
        ]
    }


@router.get("/conflict-resolutions")
async def list_conflict_resolutions():
    """List available conflict resolution strategies."""
    from src.crm_sync.sync_engine import ConflictResolution
    
    return {
        "strategies": [
            {"value": c.value, "name": c.name}
            for c in ConflictResolution
        ]
    }
