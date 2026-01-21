"""
Audit Routes - Audit Log API Endpoints
=======================================
REST API for viewing and searching audit logs.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.audit.audit_service import (
    get_audit_service,
    AuditAction,
    ResourceType,
    AuditSeverity,
)

router = APIRouter(prefix="/audit", tags=["audit"])


class LogEntryRequest(BaseModel):
    """Request to manually log an audit entry."""
    action: str
    resource_type: str
    description: str
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    severity: Optional[str] = None
    metadata: Optional[dict] = None
    tags: Optional[list[str]] = None


@router.get("")
async def search_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ip_address: Optional[str] = None,
    q: Optional[str] = None,
    tags: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=100)
):
    """Search audit logs with filters."""
    service = get_audit_service()
    
    # Parse enums
    action_enum = AuditAction(action) if action else None
    resource_type_enum = ResourceType(resource_type) if resource_type else None
    severity_enum = AuditSeverity(severity) if severity else None
    
    # Parse dates
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    # Parse tags
    tag_list = tags.split(",") if tags else None
    
    result = await service.search(
        action=action_enum,
        resource_type=resource_type_enum,
        resource_id=resource_id,
        user_id=user_id,
        user_email=user_email,
        severity=severity_enum,
        start_date=start_dt,
        end_date=end_dt,
        ip_address=ip_address,
        query=q,
        tags=tag_list,
        page=page,
        page_size=page_size
    )
    
    return {
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action.value,
                "resource_type": e.resource_type.value,
                "resource_id": e.resource_id,
                "user_id": e.user_id,
                "user_email": e.user_email,
                "ip_address": e.ip_address,
                "description": e.description,
                "severity": e.severity.value,
                "endpoint": e.endpoint,
                "method": e.method,
                "status_code": e.status_code,
                "duration_ms": e.duration_ms,
                "tags": e.tags
            }
            for e in result.entries
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "has_more": result.has_more
    }


@router.get("/stats")
async def get_audit_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get audit log statistics."""
    service = get_audit_service()
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    stats = await service.get_stats(start_date=start_dt, end_date=end_dt)
    
    return {
        "total_entries": stats.total_entries,
        "actions_by_type": stats.actions_by_type,
        "resources_by_type": stats.resources_by_type,
        "entries_by_severity": stats.entries_by_severity,
        "entries_by_hour": stats.entries_by_hour,
        "top_users": stats.top_users,
        "recent_errors": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action.value,
                "description": e.description,
                "resource_type": e.resource_type.value
            }
            for e in stats.recent_errors
        ]
    }


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    limit: int = Query(default=50, le=200)
):
    """Get audit history for a specific resource."""
    service = get_audit_service()
    
    try:
        rt_enum = ResourceType(resource_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")
    
    entries = await service.get_resource_history(
        resource_type=rt_enum,
        resource_id=resource_id,
        limit=limit
    )
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action.value,
                "user_id": e.user_id,
                "user_email": e.user_email,
                "description": e.description,
                "old_values": e.old_values,
                "new_values": e.new_values
            }
            for e in entries
        ],
        "count": len(entries)
    }


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: str,
    start_date: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """Get all activity for a specific user."""
    service = get_audit_service()
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    
    entries = await service.get_user_activity(
        user_id=user_id,
        start_date=start_dt,
        limit=limit
    )
    
    return {
        "user_id": user_id,
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "action": e.action.value,
                "resource_type": e.resource_type.value,
                "resource_id": e.resource_id,
                "description": e.description,
                "ip_address": e.ip_address
            }
            for e in entries
        ],
        "count": len(entries)
    }


@router.get("/entry/{entry_id}")
async def get_audit_entry(entry_id: str):
    """Get a specific audit entry by ID."""
    service = get_audit_service()
    
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    
    return {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "action": entry.action.value,
        "resource_type": entry.resource_type.value,
        "resource_id": entry.resource_id,
        "user_id": entry.user_id,
        "user_email": entry.user_email,
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "description": entry.description,
        "severity": entry.severity.value,
        "old_values": entry.old_values,
        "new_values": entry.new_values,
        "request_id": entry.request_id,
        "endpoint": entry.endpoint,
        "method": entry.method,
        "status_code": entry.status_code,
        "duration_ms": entry.duration_ms,
        "metadata": entry.metadata,
        "tags": entry.tags,
        "session_id": entry.session_id,
        "organization_id": entry.organization_id
    }


@router.post("")
async def log_audit_entry(request: LogEntryRequest):
    """Manually log an audit entry."""
    service = get_audit_service()
    
    try:
        action_enum = AuditAction(request.action)
        resource_type_enum = ResourceType(request.resource_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    severity_enum = AuditSeverity(request.severity) if request.severity else AuditSeverity.INFO
    
    entry = await service.log(
        action=action_enum,
        resource_type=resource_type_enum,
        description=request.description,
        resource_id=request.resource_id,
        user_id=request.user_id,
        user_email=request.user_email,
        severity=severity_enum,
        metadata=request.metadata,
        tags=request.tags
    )
    
    return {
        "success": True,
        "entry": {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "action": entry.action.value
        }
    }


@router.get("/export")
async def export_audit_logs(
    format: str = Query(default="json"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Export audit logs."""
    service = get_audit_service()
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    result = await service.export_entries(
        format=format,
        start_date=start_dt,
        end_date=end_dt
    )
    
    return result


@router.post("/cleanup")
async def cleanup_old_entries(
    days: int = Query(default=90, ge=1, le=365)
):
    """Remove audit entries older than specified days."""
    service = get_audit_service()
    
    removed = await service.cleanup_old_entries(days=days)
    
    return {
        "success": True,
        "removed_entries": removed,
        "retention_days": days
    }


@router.get("/actions")
async def list_action_types():
    """List all available audit action types."""
    return {
        "actions": [
            {"value": a.value, "name": a.name}
            for a in AuditAction
        ]
    }


@router.get("/resource-types")
async def list_resource_types():
    """List all available resource types."""
    return {
        "resource_types": [
            {"value": r.value, "name": r.name}
            for r in ResourceType
        ]
    }
