"""
Custom Fields Routes - Dynamic Field API
=========================================
REST API endpoints for custom field definitions and values.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel

from ..custom_fields import (
    CustomFieldsService,
    FieldType,
    EntityType,
    get_custom_fields_service,
)


router = APIRouter(prefix="/custom-fields", tags=["Custom Fields"])


# Request models
class CreateFieldRequest(BaseModel):
    """Create field request."""
    name: str
    entity_type: str
    field_type: str
    label: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    options: Optional[list[dict[str, Any]]] = None
    validation: Optional[dict[str, Any]] = None
    group: Optional[str] = None
    searchable: bool = False
    filterable: bool = True
    sortable: bool = True


class UpdateFieldRequest(BaseModel):
    """Update field request."""
    label: Optional[str] = None
    description: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    group: Optional[str] = None
    sort_order: Optional[int] = None
    show_in_list: Optional[bool] = None
    show_in_detail: Optional[bool] = None
    show_in_create: Optional[bool] = None
    show_in_edit: Optional[bool] = None
    searchable: Optional[bool] = None
    filterable: Optional[bool] = None
    sortable: Optional[bool] = None
    is_active: Optional[bool] = None


class AddOptionRequest(BaseModel):
    """Add option request."""
    value: str
    label: str
    color: Optional[str] = None


class ReorderOptionsRequest(BaseModel):
    """Reorder options request."""
    option_order: list[str]


class SetValueRequest(BaseModel):
    """Set value request."""
    entity_id: str
    value: Any


class BulkSetValuesRequest(BaseModel):
    """Bulk set values request."""
    entity_id: str
    values: dict[str, Any]


class CreateGroupRequest(BaseModel):
    """Create group request."""
    name: str
    entity_type: str
    description: Optional[str] = None


def get_service() -> CustomFieldsService:
    """Get custom fields service instance."""
    return get_custom_fields_service()


# Field types and entity types
@router.get("/types")
async def list_field_types():
    """List available field types."""
    return {
        "field_types": [
            {"value": t.value, "name": t.name}
            for t in FieldType
        ]
    }


@router.get("/entity-types")
async def list_entity_types():
    """List entity types that can have custom fields."""
    return {
        "entity_types": [
            {"value": e.value, "name": e.name}
            for e in EntityType
        ]
    }


# Field CRUD
@router.post("")
async def create_field(request: CreateFieldRequest):
    """Create a new custom field."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    try:
        field_type = FieldType(request.field_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid field type")
    
    custom_field = await service.create_field(
        name=request.name,
        entity_type=entity_type,
        field_type=field_type,
        label=request.label,
        description=request.description,
        options=request.options,
        validation=request.validation,
        default_value=request.default_value,
        placeholder=request.placeholder,
        help_text=request.help_text,
        group=request.group,
        searchable=request.searchable,
        filterable=request.filterable,
        sortable=request.sortable,
    )
    
    return {
        "id": custom_field.id,
        "name": custom_field.name,
        "api_name": custom_field.api_name,
        "entity_type": custom_field.entity_type.value,
        "field_type": custom_field.field_type.value,
    }


@router.get("")
async def list_fields(
    entity_type: Optional[str] = None,
    field_type: Optional[str] = None,
    group: Optional[str] = None,
    active_only: bool = True,
    include_system: bool = True,
):
    """List custom fields with filters."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    ftype = None
    if field_type:
        try:
            ftype = FieldType(field_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid field type")
    
    fields = await service.list_fields(
        entity_type=entity,
        field_type=ftype,
        group=group,
        active_only=active_only,
        include_system=include_system,
    )
    
    return {
        "fields": [
            {
                "id": f.id,
                "name": f.name,
                "api_name": f.api_name,
                "entity_type": f.entity_type.value,
                "field_type": f.field_type.value,
                "label": f.label,
                "is_system": f.is_system,
                "is_active": f.is_active,
                "sort_order": f.sort_order,
                "group": f.group,
            }
            for f in fields
        ]
    }


@router.get("/{field_id}")
async def get_field(field_id: str):
    """Get custom field by ID."""
    service = get_service()
    custom_field = await service.get_field(field_id)
    
    if not custom_field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    return {
        "id": custom_field.id,
        "name": custom_field.name,
        "api_name": custom_field.api_name,
        "entity_type": custom_field.entity_type.value,
        "field_type": custom_field.field_type.value,
        "label": custom_field.label,
        "description": custom_field.description,
        "placeholder": custom_field.placeholder,
        "help_text": custom_field.help_text,
        "default_value": custom_field.default_value,
        "options": [
            {
                "value": o.value,
                "label": o.label,
                "color": o.color,
                "is_default": o.is_default,
                "is_active": o.is_active,
            }
            for o in custom_field.options
        ],
        "validation": {
            "required": custom_field.validation.required,
            "min_value": custom_field.validation.min_value,
            "max_value": custom_field.validation.max_value,
            "min_length": custom_field.validation.min_length,
            "max_length": custom_field.validation.max_length,
            "pattern": custom_field.validation.pattern,
            "unique": custom_field.validation.unique,
        },
        "group": custom_field.group,
        "is_system": custom_field.is_system,
        "is_active": custom_field.is_active,
        "show_in_list": custom_field.show_in_list,
        "show_in_detail": custom_field.show_in_detail,
        "show_in_create": custom_field.show_in_create,
        "show_in_edit": custom_field.show_in_edit,
        "searchable": custom_field.searchable,
        "filterable": custom_field.filterable,
        "sortable": custom_field.sortable,
        "created_at": custom_field.created_at.isoformat(),
        "updated_at": custom_field.updated_at.isoformat(),
    }


@router.patch("/{field_id}")
async def update_field(field_id: str, request: UpdateFieldRequest):
    """Update custom field."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    custom_field = await service.update_field(field_id, updates)
    
    if not custom_field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    return {"success": True, "field_id": field_id}


@router.delete("/{field_id}")
async def delete_field(field_id: str):
    """Delete custom field."""
    service = get_service()
    
    if not await service.delete_field(field_id):
        raise HTTPException(status_code=400, detail="Cannot delete field (not found or is system field)")
    
    return {"success": True}


@router.get("/{field_id}/usage")
async def get_field_usage(field_id: str):
    """Get usage statistics for a field."""
    service = get_service()
    usage = await service.get_field_usage(field_id)
    
    if not usage:
        raise HTTPException(status_code=404, detail="Field not found")
    
    return usage


# Field options
@router.post("/{field_id}/options")
async def add_option(field_id: str, request: AddOptionRequest):
    """Add option to a select field."""
    service = get_service()
    
    option = await service.add_option(
        field_id=field_id,
        value=request.value,
        label=request.label,
        color=request.color,
    )
    
    if not option:
        raise HTTPException(status_code=400, detail="Cannot add option (field not found or not a select field)")
    
    return {
        "value": option.value,
        "label": option.label,
        "color": option.color,
    }


@router.delete("/{field_id}/options/{option_value}")
async def remove_option(field_id: str, option_value: str):
    """Remove option from a select field."""
    service = get_service()
    
    if not await service.remove_option(field_id, option_value):
        raise HTTPException(status_code=404, detail="Option not found")
    
    return {"success": True}


@router.post("/{field_id}/options/reorder")
async def reorder_options(field_id: str, request: ReorderOptionsRequest):
    """Reorder field options."""
    service = get_service()
    
    if not await service.reorder_options(field_id, request.option_order):
        raise HTTPException(status_code=404, detail="Field not found")
    
    return {"success": True}


# Field values
@router.post("/{field_id}/values")
async def set_value(field_id: str, request: SetValueRequest):
    """Set a custom field value for an entity."""
    service = get_service()
    
    field_value = await service.set_value(
        field_id=field_id,
        entity_id=request.entity_id,
        value=request.value,
    )
    
    if not field_value:
        raise HTTPException(status_code=400, detail="Cannot set value (field not found or validation failed)")
    
    return {
        "id": field_value.id,
        "field_id": field_value.field_id,
        "entity_id": field_value.entity_id,
        "value": field_value.value,
        "display_value": field_value.display_value,
    }


@router.get("/{field_id}/values/{entity_id}")
async def get_value(field_id: str, entity_id: str):
    """Get a custom field value."""
    service = get_service()
    field_value = await service.get_value(field_id, entity_id)
    
    if not field_value:
        return {"field_id": field_id, "entity_id": entity_id, "value": None}
    
    return {
        "id": field_value.id,
        "field_id": field_value.field_id,
        "entity_id": field_value.entity_id,
        "value": field_value.value,
        "display_value": field_value.display_value,
    }


@router.delete("/{field_id}/values/{entity_id}")
async def delete_value(field_id: str, entity_id: str):
    """Delete a custom field value."""
    service = get_service()
    
    if not await service.delete_value(field_id, entity_id):
        raise HTTPException(status_code=404, detail="Value not found")
    
    return {"success": True}


# Entity values
@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_values(
    entity_type: str,
    entity_id: str,
    include_empty: bool = False
):
    """Get all custom field values for an entity."""
    service = get_service()
    
    try:
        entity = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    values = await service.get_entity_values(entity, entity_id, include_empty)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "values": values,
    }


@router.post("/entity/{entity_type}/bulk")
async def bulk_set_values(entity_type: str, request: BulkSetValuesRequest):
    """Bulk set custom field values for an entity."""
    service = get_service()
    
    try:
        entity = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    results = await service.bulk_set_values(
        entity_type=entity,
        entity_id=request.entity_id,
        values=request.values,
    )
    
    return {
        "entity_id": request.entity_id,
        "results": results,
        "success_count": sum(1 for v in results.values() if v),
        "error_count": sum(1 for v in results.values() if not v),
    }


# Field groups
@router.post("/groups")
async def create_group(request: CreateGroupRequest):
    """Create a field group."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    group = await service.create_group(
        name=request.name,
        entity_type=entity_type,
        description=request.description,
    )
    
    return {
        "id": group.id,
        "name": group.name,
        "entity_type": group.entity_type.value,
    }


@router.get("/groups")
async def list_groups(
    entity_type: Optional[str] = None,
    active_only: bool = True,
):
    """List field groups."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    groups = await service.list_groups(entity, active_only)
    
    return {
        "groups": [
            {
                "id": g.id,
                "name": g.name,
                "entity_type": g.entity_type.value,
                "description": g.description,
                "sort_order": g.sort_order,
                "is_expanded": g.is_expanded,
                "is_active": g.is_active,
            }
            for g in groups
        ]
    }
