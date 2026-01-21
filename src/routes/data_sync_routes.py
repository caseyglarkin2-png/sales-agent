"""
Data Sync Routes - Synchronization API
=======================================
REST API endpoints for data synchronization and conflict resolution.
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Optional
from pydantic import BaseModel

from ..data_sync import (
    DataSyncService,
    SyncOperation,
    SyncStatus,
    ConflictResolution,
    get_data_sync_service,
)
from ..data_sync.data_sync_service import EntityType


router = APIRouter(prefix="/sync", tags=["Data Sync"])


# Request models
class PushChangesRequest(BaseModel):
    """Push changes request."""
    client_id: str
    user_id: str
    changes: list[dict[str, Any]]


class PullChangesRequest(BaseModel):
    """Pull changes request."""
    client_id: str
    user_id: str
    since_token: Optional[str] = None
    entity_types: Optional[list[str]] = None


class RecordChangeRequest(BaseModel):
    """Record change request."""
    entity_type: str
    entity_id: str
    operation: str
    data: dict[str, Any]
    previous_data: Optional[dict[str, Any]] = None
    user_id: Optional[str] = None
    device_id: Optional[str] = None


class ResolveConflictRequest(BaseModel):
    """Resolve conflict request."""
    resolution: str
    resolved_data: Optional[dict[str, Any]] = None
    resolved_by: Optional[str] = None


def get_service() -> DataSyncService:
    """Get data sync service instance."""
    return get_data_sync_service()


# Enums
@router.get("/operations")
async def list_operations():
    """List available sync operations."""
    return {
        "operations": [
            {"value": o.value, "name": o.name}
            for o in SyncOperation
        ]
    }


@router.get("/statuses")
async def list_statuses():
    """List sync statuses."""
    return {
        "statuses": [
            {"value": s.value, "name": s.name}
            for s in SyncStatus
        ]
    }


@router.get("/resolutions")
async def list_resolutions():
    """List conflict resolution strategies."""
    return {
        "resolutions": [
            {"value": r.value, "name": r.name}
            for r in ConflictResolution
        ]
    }


@router.get("/entity-types")
async def list_entity_types():
    """List entity types for sync."""
    return {
        "entity_types": [
            {"value": e.value, "name": e.name}
            for e in EntityType
        ]
    }


# Sync operations
@router.post("/push")
async def push_changes(request: PushChangesRequest):
    """Push changes from client to server."""
    service = get_service()
    
    result = await service.push_changes(
        client_id=request.client_id,
        user_id=request.user_id,
        changes=request.changes,
    )
    
    return result


@router.post("/pull")
async def pull_changes(request: PullChangesRequest):
    """Pull changes from server to client."""
    service = get_service()
    
    entity_types = None
    if request.entity_types:
        entity_types = []
        for et in request.entity_types:
            try:
                entity_types.append(EntityType(et))
            except ValueError:
                pass
    
    result = await service.pull_changes(
        client_id=request.client_id,
        user_id=request.user_id,
        since_token=request.since_token,
        entity_types=entity_types,
    )
    
    return result


@router.post("/changes")
async def record_change(request: RecordChangeRequest):
    """Record a data change."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    try:
        operation = SyncOperation(request.operation)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid operation")
    
    change = await service.record_change(
        entity_type=entity_type,
        entity_id=request.entity_id,
        operation=operation,
        data=request.data,
        previous_data=request.previous_data,
        user_id=request.user_id,
        device_id=request.device_id,
    )
    
    return {
        "id": change.id,
        "entity_type": change.entity_type.value,
        "entity_id": change.entity_id,
        "operation": change.operation.value,
        "version": change.version,
        "checksum": change.checksum,
        "timestamp": change.timestamp.isoformat(),
    }


@router.get("/changes")
async def get_changes(
    since_token: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 1000,
):
    """Get changes since a sync token."""
    service = get_service()
    
    entity_types = None
    if entity_type:
        try:
            entity_types = [EntityType(entity_type)]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    changes, new_token = await service.get_changes_since(
        since_token=since_token,
        entity_types=entity_types,
        limit=limit,
    )
    
    return {
        "changes": [
            {
                "id": c.id,
                "entity_type": c.entity_type.value,
                "entity_id": c.entity_id,
                "operation": c.operation.value,
                "version": c.version,
                "data": c.data,
                "changed_fields": c.changed_fields,
                "timestamp": c.timestamp.isoformat(),
            }
            for c in changes
        ],
        "sync_token": new_token,
        "count": len(changes),
    }


# Entity operations
@router.get("/entity/{entity_type}/{entity_id}/version")
async def get_entity_version(entity_type: str, entity_id: str):
    """Get current version of an entity."""
    service = get_service()
    
    try:
        etype = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    version = await service.get_entity_version(etype, entity_id)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "version": version,
    }


@router.get("/entity/{entity_type}/{entity_id}/history")
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
):
    """Get change history for an entity."""
    service = get_service()
    
    try:
        etype = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    history = await service.get_entity_history(etype, entity_id, limit)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "history": [
            {
                "id": c.id,
                "operation": c.operation.value,
                "version": c.version,
                "changed_fields": c.changed_fields,
                "timestamp": c.timestamp.isoformat(),
                "user_id": c.user_id,
            }
            for c in history
        ],
    }


# Conflicts
@router.get("/conflicts")
async def list_conflicts(
    resolved: Optional[bool] = None,
):
    """List sync conflicts."""
    service = get_service()
    conflicts = await service.list_conflicts(resolved=resolved)
    
    return {
        "conflicts": [
            {
                "id": c.id,
                "entity_type": c.entity_type.value,
                "entity_id": c.entity_id,
                "local_version": c.local_version,
                "server_version": c.server_version,
                "conflicting_fields": c.conflicting_fields,
                "resolution": c.resolution.value if c.resolution else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in conflicts
        ]
    }


@router.get("/conflicts/{conflict_id}")
async def get_conflict(conflict_id: str):
    """Get conflict by ID."""
    service = get_service()
    conflict = await service.get_conflict(conflict_id)
    
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    return {
        "id": conflict.id,
        "entity_type": conflict.entity_type.value,
        "entity_id": conflict.entity_id,
        "local_version": conflict.local_version,
        "server_version": conflict.server_version,
        "local_data": conflict.local_data,
        "server_data": conflict.server_data,
        "conflicting_fields": conflict.conflicting_fields,
        "resolution": conflict.resolution.value if conflict.resolution else None,
        "resolved_data": conflict.resolved_data,
        "resolved_at": conflict.resolved_at.isoformat() if conflict.resolved_at else None,
        "resolved_by": conflict.resolved_by,
        "created_at": conflict.created_at.isoformat(),
    }


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, request: ResolveConflictRequest):
    """Resolve a sync conflict."""
    service = get_service()
    
    try:
        resolution = ConflictResolution(request.resolution)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resolution strategy")
    
    conflict = await service.resolve_conflict(
        conflict_id=conflict_id,
        resolution=resolution,
        resolved_data=request.resolved_data,
        resolved_by=request.resolved_by,
    )
    
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found or resolution failed")
    
    return {
        "id": conflict.id,
        "resolution": conflict.resolution.value,
        "resolved": True,
    }


# Client state
@router.get("/clients/{client_id}")
async def get_client_state(client_id: str):
    """Get client sync state."""
    service = get_service()
    state = await service.get_client_state(client_id)
    
    if not state:
        return {"client_id": client_id, "state": None}
    
    return {
        "client_id": state.client_id,
        "user_id": state.user_id,
        "last_sync_at": state.last_sync_at.isoformat() if state.last_sync_at else None,
        "last_sync_token": state.last_sync_token,
        "pending_changes": len(state.pending_changes),
        "tracked_entities": len(state.version_map),
    }


# Stats
@router.get("/stats")
async def get_sync_stats():
    """Get sync statistics."""
    service = get_service()
    return await service.get_sync_stats()
