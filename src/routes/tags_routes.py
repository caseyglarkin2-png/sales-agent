"""
Tags Routes - Tagging API
=========================
REST API endpoints for tag management and entity tagging.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel

from ..tags import (
    TagsService,
    get_tags_service,
)
from ..tags.tags_service import EntityType


router = APIRouter(prefix="/tags", tags=["Tags"])


# Request models
class CreateTagRequest(BaseModel):
    """Create tag request."""
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    allowed_entity_types: Optional[list[str]] = None


class UpdateTagRequest(BaseModel):
    """Update tag request."""
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    is_active: Optional[bool] = None


class TagEntityRequest(BaseModel):
    """Tag entity request."""
    entity_type: str
    entity_id: str


class BulkTagRequest(BaseModel):
    """Bulk tag request."""
    tag_ids: list[str]
    entity_type: str
    entity_id: str


class ReplaceTagsRequest(BaseModel):
    """Replace tags request."""
    entity_type: str
    entity_id: str
    tag_ids: list[str]


class CreateCategoryRequest(BaseModel):
    """Create category request."""
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


def get_service() -> TagsService:
    """Get tags service instance."""
    return get_tags_service()


# Tag CRUD
@router.post("")
async def create_tag(request: CreateTagRequest):
    """Create a new tag."""
    service = get_service()
    
    allowed_types = None
    if request.allowed_entity_types:
        allowed_types = []
        for t in request.allowed_entity_types:
            try:
                allowed_types.append(EntityType(t))
            except ValueError:
                pass
    
    tag = await service.create_tag(
        name=request.name,
        color=request.color,
        description=request.description,
        category_id=request.category_id,
        allowed_entity_types=allowed_types,
    )
    
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "color": tag.color,
    }


@router.get("")
async def list_tags(
    category_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    include_system: bool = True,
):
    """List tags with filters."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    tags = await service.list_tags(
        category_id=category_id,
        entity_type=entity,
        search=search,
        active_only=active_only,
        include_system=include_system,
    )
    
    return {
        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
                "description": t.description,
                "usage_count": t.usage_count,
                "is_system": t.is_system,
                "is_active": t.is_active,
            }
            for t in tags
        ]
    }


@router.get("/search")
async def search_tags(
    q: str,
    limit: int = 10
):
    """Search tags by name."""
    service = get_service()
    tags = await service.search_tags(q, limit)
    
    return {
        "query": q,
        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
            }
            for t in tags
        ]
    }


@router.get("/popular")
async def get_popular_tags(
    entity_type: Optional[str] = None,
    limit: int = 10
):
    """Get most popular tags."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    tags = await service.get_popular_tags(entity, limit)
    
    return {"popular_tags": tags}


@router.get("/stats")
async def get_tag_stats():
    """Get tag statistics."""
    service = get_service()
    return await service.get_tag_stats()


@router.get("/entity-types")
async def list_entity_types():
    """List entity types that can be tagged."""
    return {
        "entity_types": [
            {"value": e.value, "name": e.name}
            for e in EntityType
        ]
    }


@router.get("/{tag_id}")
async def get_tag(tag_id: str):
    """Get tag by ID."""
    service = get_service()
    tag = await service.get_tag(tag_id)
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "color": tag.color,
        "description": tag.description,
        "category_id": tag.category_id,
        "allowed_entity_types": [t.value for t in tag.allowed_entity_types],
        "usage_count": tag.usage_count,
        "is_system": tag.is_system,
        "is_active": tag.is_active,
        "created_at": tag.created_at.isoformat(),
        "updated_at": tag.updated_at.isoformat(),
    }


@router.get("/slug/{slug}")
async def get_tag_by_slug(slug: str):
    """Get tag by slug."""
    service = get_service()
    tag = await service.get_tag_by_slug(slug)
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "color": tag.color,
    }


@router.patch("/{tag_id}")
async def update_tag(tag_id: str, request: UpdateTagRequest):
    """Update tag."""
    service = get_service()
    
    updates = request.model_dump(exclude_unset=True)
    tag = await service.update_tag(tag_id, updates)
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return {"success": True, "tag_id": tag_id}


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str):
    """Delete tag."""
    service = get_service()
    
    if not await service.delete_tag(tag_id):
        raise HTTPException(status_code=400, detail="Cannot delete tag (not found or is system tag)")
    
    return {"success": True}


# Tagging operations
@router.post("/{tag_id}/tag")
async def tag_entity(tag_id: str, request: TagEntityRequest):
    """Tag an entity."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    entity_tag = await service.tag_entity(
        tag_id=tag_id,
        entity_type=entity_type,
        entity_id=request.entity_id,
    )
    
    if not entity_tag:
        raise HTTPException(status_code=400, detail="Cannot tag entity (tag not found or not allowed)")
    
    return {
        "id": entity_tag.id,
        "tag_id": entity_tag.tag_id,
        "entity_type": entity_tag.entity_type.value,
        "entity_id": entity_tag.entity_id,
        "tagged_at": entity_tag.tagged_at.isoformat(),
    }


@router.post("/{tag_id}/untag")
async def untag_entity(tag_id: str, request: TagEntityRequest):
    """Remove tag from an entity."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    if not await service.untag_entity(tag_id, entity_type, request.entity_id):
        raise HTTPException(status_code=404, detail="Tag association not found")
    
    return {"success": True}


@router.get("/{tag_id}/entities")
async def get_tagged_entities(
    tag_id: str,
    entity_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get all entities with a specific tag."""
    service = get_service()
    
    entity = None
    if entity_type:
        try:
            entity = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid entity type")
    
    entities = await service.get_tagged_entities(tag_id, entity, limit, offset)
    
    return {
        "tag_id": tag_id,
        "entities": entities,
        "count": len(entities),
    }


# Entity tags
@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_tags(entity_type: str, entity_id: str):
    """Get all tags for an entity."""
    service = get_service()
    
    try:
        entity = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    tags = await service.get_entity_tags(entity, entity_id)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
            }
            for t in tags
        ]
    }


@router.post("/bulk-tag")
async def bulk_tag(request: BulkTagRequest):
    """Apply multiple tags to an entity."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    results = await service.bulk_tag(
        tag_ids=request.tag_ids,
        entity_type=entity_type,
        entity_id=request.entity_id,
    )
    
    return {
        "entity_id": request.entity_id,
        "results": results,
        "success_count": sum(1 for v in results.values() if v),
    }


@router.post("/replace")
async def replace_tags(request: ReplaceTagsRequest):
    """Replace all tags on an entity."""
    service = get_service()
    
    try:
        entity_type = EntityType(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    tags = await service.replace_tags(
        entity_type=entity_type,
        entity_id=request.entity_id,
        tag_ids=request.tag_ids,
    )
    
    return {
        "entity_id": request.entity_id,
        "tags": [
            {"id": t.id, "name": t.name}
            for t in tags
        ]
    }


# Categories
@router.post("/categories")
async def create_category(request: CreateCategoryRequest):
    """Create a tag category."""
    service = get_service()
    
    category = await service.create_category(
        name=request.name,
        description=request.description,
        color=request.color,
    )
    
    return {
        "id": category.id,
        "name": category.name,
    }


@router.get("/categories")
async def list_categories(active_only: bool = True):
    """List tag categories."""
    service = get_service()
    categories = await service.list_categories(active_only)
    
    return {
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "color": c.color,
                "sort_order": c.sort_order,
                "is_active": c.is_active,
            }
            for c in categories
        ]
    }


@router.get("/categories/{category_id}/tags")
async def get_tags_by_category(category_id: str, active_only: bool = True):
    """Get all tags in a category."""
    service = get_service()
    tags = await service.get_tags_by_category(category_id, active_only)
    
    return {
        "category_id": category_id,
        "tags": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
                "usage_count": t.usage_count,
            }
            for t in tags
        ]
    }
