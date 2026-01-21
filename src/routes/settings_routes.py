"""
Settings Routes - Settings Management API
==========================================
REST API for application settings.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any

from src.settings_manager.settings_service import (
    get_settings_service,
    SettingCategory,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class UpdateSettingRequest(BaseModel):
    """Request to update a setting."""
    value: Any


class BulkUpdateRequest(BaseModel):
    """Request to update multiple settings."""
    settings: dict[str, Any]


class ImportSettingsRequest(BaseModel):
    """Request to import settings."""
    settings: dict[str, Any]


@router.get("")
async def get_all_settings(
    category: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get all settings."""
    service = get_settings_service()
    
    category_enum = SettingCategory(category) if category else None
    
    settings = await service.get_all(
        category=category_enum,
        org_id=org_id,
        user_id=user_id
    )
    
    # Group by category
    grouped = {}
    for key, data in settings.items():
        cat = data["category"]
        if cat not in grouped:
            grouped[cat] = {}
        grouped[cat][key] = data
    
    return {"settings": grouped}


@router.get("/categories")
async def list_categories():
    """List all setting categories."""
    service = get_settings_service()
    
    categories = await service.get_categories()
    
    return {"categories": categories}


@router.get("/category/{category}")
async def get_settings_by_category(
    category: str,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get all settings in a category."""
    service = get_settings_service()
    
    try:
        category_enum = SettingCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    
    settings = await service.get_by_category(
        category=category_enum,
        org_id=org_id,
        user_id=user_id
    )
    
    return {
        "category": category,
        "settings": settings
    }


@router.get("/definition/{key}")
async def get_setting_definition(key: str):
    """Get the definition for a setting."""
    service = get_settings_service()
    
    definition = await service.get_definition(key)
    if not definition:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return definition


@router.get("/{key}")
async def get_setting(
    key: str,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Get a specific setting value."""
    service = get_settings_service()
    
    value = await service.get(key, org_id=org_id, user_id=user_id)
    definition = await service.get_definition(key)
    
    if definition is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    # Mask sensitive values
    if definition.get("is_sensitive") and value:
        value = "********"
    
    return {
        "key": key,
        "value": value,
        "definition": definition
    }


@router.put("/{key}")
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Update a setting value."""
    service = get_settings_service()
    
    success = await service.set(
        key=key,
        value=request.value,
        org_id=org_id,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update setting")
    
    return {
        "success": True,
        "key": key,
        "value": request.value
    }


@router.delete("/{key}")
async def reset_setting(
    key: str,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Reset a setting to its default value."""
    service = get_settings_service()
    
    success = await service.reset_to_default(
        key=key,
        org_id=org_id,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    # Get new value
    value = await service.get(key, org_id=org_id, user_id=user_id)
    
    return {
        "success": True,
        "key": key,
        "value": value,
        "is_default": True
    }


@router.post("/bulk")
async def bulk_update_settings(
    request: BulkUpdateRequest,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Update multiple settings at once."""
    service = get_settings_service()
    
    results = await service.bulk_update(
        settings=request.settings,
        org_id=org_id,
        user_id=user_id
    )
    
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count
    
    return {
        "success": failed_count == 0,
        "updated": success_count,
        "failed": failed_count,
        "results": results
    }


@router.get("/export/all")
async def export_settings(org_id: Optional[str] = None):
    """Export all settings for backup."""
    service = get_settings_service()
    
    export_data = await service.export_settings(org_id=org_id)
    
    return export_data


@router.post("/import")
async def import_settings(
    request: ImportSettingsRequest,
    org_id: Optional[str] = None
):
    """Import settings from backup."""
    service = get_settings_service()
    
    results = await service.import_settings(
        settings=request.settings,
        org_id=org_id
    )
    
    success_count = sum(1 for v in results.values() if v)
    
    return {
        "success": True,
        "imported": success_count,
        "failed": len(results) - success_count
    }
