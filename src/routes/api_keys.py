"""
API Key Routes - API Key Management Endpoints
==============================================
REST API for managing API keys.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from src.api_keys.api_key_service import (
    get_api_key_service,
    APIKeyPermission,
    APIKeyStatus,
    RateLimit,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    """Request to create an API key."""
    name: str
    permissions: list[str]
    description: Optional[str] = None
    expires_in_days: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    allowed_ips: Optional[list[str]] = None
    allowed_origins: Optional[list[str]] = None


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key."""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None
    allowed_ips: Optional[list[str]] = None
    allowed_origins: Optional[list[str]] = None


class ValidateKeyRequest(BaseModel):
    """Request to validate an API key."""
    api_key: str
    required_permissions: Optional[list[str]] = None
    client_ip: Optional[str] = None
    origin: Optional[str] = None


@router.post("")
async def create_api_key(request: CreateAPIKeyRequest):
    """Create a new API key."""
    service = get_api_key_service()
    
    # Parse permissions
    try:
        permissions = [APIKeyPermission(p) for p in request.permissions]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid permission: {e}")
    
    # Build rate limit
    rate_limit = None
    if any([request.rate_limit_per_minute, request.rate_limit_per_hour, request.rate_limit_per_day]):
        rate_limit = RateLimit(
            requests_per_minute=request.rate_limit_per_minute or 60,
            requests_per_hour=request.rate_limit_per_hour or 1000,
            requests_per_day=request.rate_limit_per_day or 10000
        )
    
    api_key, raw_key = await service.create_api_key(
        name=request.name,
        permissions=permissions,
        description=request.description,
        expires_in_days=request.expires_in_days,
        rate_limit=rate_limit,
        allowed_ips=request.allowed_ips,
        allowed_origins=request.allowed_origins
    )
    
    return {
        "success": True,
        "api_key": {
            "id": api_key.id,
            "name": api_key.name,
            "key": raw_key,  # Only shown once!
            "key_prefix": api_key.key_prefix,
            "permissions": [p.value for p in api_key.permissions],
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "created_at": api_key.created_at.isoformat()
        },
        "warning": "This is the only time the full API key will be shown. Store it securely."
    }


@router.get("")
async def list_api_keys(
    status: Optional[str] = None,
    created_by: Optional[str] = None
):
    """List all API keys."""
    service = get_api_key_service()
    
    status_enum = APIKeyStatus(status) if status else None
    
    keys = await service.list_api_keys(
        status=status_enum,
        created_by=created_by
    )
    
    return {
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "permissions": [p.value for p in k.permissions],
                "status": k.status.value,
                "total_requests": k.usage.total_requests,
                "last_used_at": k.usage.last_used_at.isoformat() if k.usage.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat()
            }
            for k in keys
        ],
        "count": len(keys)
    }


@router.get("/permissions")
async def list_permissions():
    """List all available permissions."""
    permissions_by_category = {}
    
    for perm in APIKeyPermission:
        category = perm.value.split(":")[0]
        if category not in permissions_by_category:
            permissions_by_category[category] = []
        permissions_by_category[category].append({
            "value": perm.value,
            "name": perm.name
        })
    
    return {"permissions": permissions_by_category}


@router.get("/stats")
async def get_api_key_stats():
    """Get overall API key statistics."""
    service = get_api_key_service()
    
    stats = await service.get_usage_stats()
    
    return stats


@router.post("/validate")
async def validate_api_key(request: ValidateKeyRequest):
    """Validate an API key."""
    service = get_api_key_service()
    
    required_perms = None
    if request.required_permissions:
        try:
            required_perms = [APIKeyPermission(p) for p in request.required_permissions]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permission: {e}")
    
    result = await service.validate_key(
        raw_key=request.api_key,
        required_permissions=required_perms,
        client_ip=request.client_ip,
        origin=request.origin
    )
    
    if result.is_valid:
        return {
            "valid": True,
            "key_id": result.api_key.id,
            "name": result.api_key.name,
            "permissions": [p.value for p in result.api_key.permissions]
        }
    else:
        return {
            "valid": False,
            "error": result.error
        }


@router.get("/{key_id}")
async def get_api_key(key_id: str):
    """Get API key details."""
    service = get_api_key_service()
    
    api_key = await service.get_api_key(key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "permissions": [p.value for p in api_key.permissions],
        "status": api_key.status.value,
        "description": api_key.description,
        "rate_limit": {
            "per_minute": api_key.rate_limit.requests_per_minute,
            "per_hour": api_key.rate_limit.requests_per_hour,
            "per_day": api_key.rate_limit.requests_per_day
        },
        "allowed_ips": api_key.allowed_ips,
        "allowed_origins": api_key.allowed_origins,
        "usage": {
            "total_requests": api_key.usage.total_requests,
            "requests_today": api_key.usage.requests_today,
            "requests_this_month": api_key.usage.requests_this_month,
            "last_used_at": api_key.usage.last_used_at.isoformat() if api_key.usage.last_used_at else None,
            "last_used_ip": api_key.usage.last_used_ip,
            "last_used_endpoint": api_key.usage.last_used_endpoint
        },
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "created_at": api_key.created_at.isoformat(),
        "created_by": api_key.created_by
    }


@router.get("/{key_id}/usage")
async def get_api_key_usage(key_id: str):
    """Get usage statistics for an API key."""
    service = get_api_key_service()
    
    stats = await service.get_usage_stats(key_id)
    if not stats:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return stats


@router.get("/{key_id}/rate-limit")
async def check_rate_limit(key_id: str):
    """Check rate limit status for an API key."""
    service = get_api_key_service()
    
    result = await service.check_rate_limit(key_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.patch("/{key_id}")
async def update_api_key(key_id: str, request: UpdateAPIKeyRequest):
    """Update an API key."""
    service = get_api_key_service()
    
    updates = request.dict(exclude_none=True)
    
    # Convert permissions
    if "permissions" in updates:
        try:
            updates["permissions"] = [APIKeyPermission(p) for p in updates["permissions"]]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid permission: {e}")
    
    api_key = await service.update_api_key(key_id, updates)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "success": True,
        "api_key": {
            "id": api_key.id,
            "name": api_key.name,
            "permissions": [p.value for p in api_key.permissions]
        }
    }


@router.post("/{key_id}/revoke")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    service = get_api_key_service()
    
    success = await service.revoke_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"success": True, "revoked": key_id}


@router.post("/{key_id}/rotate")
async def rotate_api_key(key_id: str):
    """Rotate an API key (create new, revoke old)."""
    service = get_api_key_service()
    
    result = await service.rotate_api_key(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
    
    new_key, raw_key = result
    
    return {
        "success": True,
        "old_key_id": key_id,
        "new_api_key": {
            "id": new_key.id,
            "name": new_key.name,
            "key": raw_key,  # Only shown once!
            "key_prefix": new_key.key_prefix
        },
        "warning": "This is the only time the new API key will be shown. Store it securely."
    }


@router.delete("/{key_id}")
async def delete_api_key(key_id: str):
    """Delete an API key."""
    service = get_api_key_service()
    
    success = await service.delete_api_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"success": True, "deleted": key_id}
