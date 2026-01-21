"""
Search Routes - Advanced Search API
====================================
REST API endpoints for search, suggestions, and saved searches.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from ..search import (
    SearchService,
    get_search_service,
)
from ..search.search_service import (
    SearchableEntity,
    SearchOperator,
    SearchFilter,
    SortOrder,
)


router = APIRouter(prefix="/search", tags=["Search"])


# Request models
class SearchRequest(BaseModel):
    """Search request."""
    query: str
    entity_types: Optional[list[str]] = None
    filters: Optional[list[dict[str, Any]]] = None
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    include_facets: bool = True
    include_suggestions: bool = True


class IndexDocumentRequest(BaseModel):
    """Index document request."""
    id: str
    entity_type: str
    title: str
    data: dict[str, Any] = {}
    subtitle: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None


class BulkIndexRequest(BaseModel):
    """Bulk index request."""
    documents: list[dict[str, Any]]


class SaveSearchRequest(BaseModel):
    """Save search request."""
    name: str
    query: str
    entity_types: list[str]
    filters: Optional[list[dict[str, Any]]] = None
    is_public: bool = False
    notification_enabled: bool = False


def get_service() -> SearchService:
    """Get search service instance."""
    return get_search_service()


def parse_filters(filters: Optional[list[dict[str, Any]]]) -> list[SearchFilter]:
    """Parse filter dictionaries to SearchFilter objects."""
    if not filters:
        return []
    
    result = []
    for f in filters:
        try:
            result.append(SearchFilter(
                field=f["field"],
                operator=SearchOperator(f.get("operator", "equals")),
                value=f.get("value"),
                boost=f.get("boost", 1.0),
            ))
        except (KeyError, ValueError):
            continue
    return result


def parse_entity_types(types: Optional[list[str]]) -> list[SearchableEntity]:
    """Parse entity type strings."""
    if not types:
        return [SearchableEntity.ALL]
    
    result = []
    for t in types:
        try:
            result.append(SearchableEntity(t))
        except ValueError:
            continue
    return result if result else [SearchableEntity.ALL]


# Enums
@router.get("/entity-types")
async def list_entity_types():
    """List searchable entity types."""
    return {
        "entity_types": [
            {"value": e.value, "name": e.name}
            for e in SearchableEntity
        ]
    }


@router.get("/operators")
async def list_operators():
    """List search operators."""
    return {
        "operators": [
            {"value": o.value, "name": o.name}
            for o in SearchOperator
        ]
    }


# Search endpoints
@router.post("")
async def search(request: SearchRequest, user_id: Optional[str] = None):
    """Execute a search query."""
    service = get_service()
    
    entity_types = parse_entity_types(request.entity_types)
    filters = parse_filters(request.filters)
    
    try:
        sort_order = SortOrder(request.sort_order)
    except ValueError:
        sort_order = SortOrder.DESC
    
    result = await service.search(
        query=request.query,
        entity_types=entity_types,
        filters=filters,
        page=request.page,
        page_size=request.page_size,
        sort_by=request.sort_by,
        sort_order=sort_order,
        include_facets=request.include_facets,
        include_suggestions=request.include_suggestions,
        user_id=user_id,
    )
    
    return {
        "query": result.query,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "took_ms": result.took_ms,
        "items": [
            {
                "id": item.id,
                "entity_type": item.entity_type.value,
                "title": item.title,
                "subtitle": item.subtitle,
                "description": item.description,
                "score": item.score,
                "highlights": item.highlights,
                "metadata": item.metadata,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "url": item.url,
            }
            for item in result.items
        ],
        "facets": {
            name: [
                {"field": f.field, "value": f.value, "count": f.count, "selected": f.selected}
                for f in facets
            ]
            for name, facets in result.facets.items()
        },
        "suggestions": [
            {
                "text": s.text,
                "highlighted": s.highlighted,
                "entity_type": s.entity_type.value,
                "entity_id": s.entity_id,
            }
            for s in result.suggestions
        ],
        "spell_corrected": result.spell_corrected,
    }


@router.get("/quick")
async def quick_search(
    q: str = Query(..., description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated entity types"),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[str] = None,
):
    """Quick search endpoint for autocomplete."""
    service = get_service()
    
    entity_types = [SearchableEntity.ALL]
    if types:
        entity_types = parse_entity_types(types.split(","))
    
    result = await service.search(
        query=q,
        entity_types=entity_types,
        page=1,
        page_size=limit,
        include_facets=False,
        include_suggestions=True,
        user_id=user_id,
    )
    
    return {
        "query": q,
        "total": result.total,
        "items": [
            {
                "id": item.id,
                "type": item.entity_type.value,
                "title": item.title,
                "subtitle": item.subtitle,
                "url": item.url,
            }
            for item in result.items
        ],
        "suggestions": [
            {"text": s.text, "highlighted": s.highlighted}
            for s in result.suggestions
        ],
    }


@router.get("/suggestions")
async def get_suggestions(
    q: str = Query(..., description="Query for suggestions"),
    types: Optional[str] = Query(None, description="Comma-separated entity types"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get search suggestions."""
    service = get_service()
    
    entity_types = None
    if types:
        entity_types = parse_entity_types(types.split(","))
    
    suggestions = await service.get_suggestions(q, entity_types, limit)
    
    return {
        "query": q,
        "suggestions": [
            {
                "text": s.text,
                "highlighted": s.highlighted,
                "entity_type": s.entity_type.value,
                "entity_id": s.entity_id,
            }
            for s in suggestions
        ],
    }


# Indexing endpoints
@router.post("/index")
async def index_document(request: IndexDocumentRequest):
    """Index a document for search."""
    service = get_service()
    
    try:
        entity_type = SearchableEntity(request.entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    await service.index_document(
        doc_id=request.id,
        entity_type=entity_type,
        title=request.title,
        data=request.data,
        subtitle=request.subtitle,
        description=request.description,
        url=request.url,
    )
    
    return {"success": True, "id": request.id}


@router.post("/index/bulk")
async def bulk_index(request: BulkIndexRequest):
    """Bulk index documents."""
    service = get_service()
    result = await service.bulk_index(request.documents)
    return result


@router.patch("/index/{doc_id}")
async def update_document(doc_id: str, data: dict[str, Any]):
    """Update an indexed document."""
    service = get_service()
    await service.update_document(doc_id, data)
    return {"success": True}


@router.delete("/index/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the index."""
    service = get_service()
    await service.delete_document(doc_id)
    return {"success": True}


@router.post("/reindex")
async def reindex_all():
    """Trigger reindexing of all documents."""
    service = get_service()
    result = await service.reindex_all()
    return result


# Saved searches
@router.post("/saved")
async def save_search(request: SaveSearchRequest, user_id: str):
    """Save a search query."""
    service = get_service()
    
    entity_types = parse_entity_types(request.entity_types)
    filters = parse_filters(request.filters)
    
    saved = await service.save_search(
        name=request.name,
        query=request.query,
        entity_types=entity_types,
        filters=filters,
        user_id=user_id,
        is_public=request.is_public,
        notification_enabled=request.notification_enabled,
    )
    
    return {
        "id": saved.id,
        "name": saved.name,
        "query": saved.query,
    }


@router.get("/saved")
async def list_saved_searches(
    user_id: str,
    include_public: bool = True,
):
    """List saved searches."""
    service = get_service()
    searches = await service.get_saved_searches(user_id, include_public)
    
    return {
        "saved_searches": [
            {
                "id": s.id,
                "name": s.name,
                "query": s.query,
                "entity_types": [e.value for e in s.entity_types],
                "is_public": s.is_public,
                "notification_enabled": s.notification_enabled,
                "use_count": s.use_count,
                "last_used": s.last_used.isoformat() if s.last_used else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in searches
        ]
    }


@router.get("/saved/{search_id}")
async def execute_saved_search(
    search_id: str,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[str] = None,
):
    """Execute a saved search."""
    service = get_service()
    result = await service.execute_saved_search(search_id, page, page_size, user_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Saved search not found")
    
    return {
        "query": result.query,
        "total": result.total,
        "page": result.page,
        "items": [
            {
                "id": item.id,
                "entity_type": item.entity_type.value,
                "title": item.title,
                "subtitle": item.subtitle,
                "score": item.score,
            }
            for item in result.items
        ],
    }


@router.delete("/saved/{search_id}")
async def delete_saved_search(search_id: str, user_id: str):
    """Delete a saved search."""
    service = get_service()
    
    if not await service.delete_saved_search(search_id, user_id):
        raise HTTPException(status_code=404, detail="Saved search not found or access denied")
    
    return {"success": True}


# Recent searches
@router.get("/recent")
async def get_recent_searches(user_id: str, limit: int = 10):
    """Get recent searches for a user."""
    service = get_service()
    recent = await service.get_recent_searches(user_id, limit)
    
    return {
        "recent_searches": [
            {
                "id": r.id,
                "query": r.query,
                "entity_types": [e.value for e in r.entity_types],
                "result_count": r.result_count,
                "searched_at": r.searched_at.isoformat(),
            }
            for r in recent
        ]
    }


@router.delete("/recent")
async def clear_recent_searches(user_id: str):
    """Clear recent searches for a user."""
    service = get_service()
    await service.clear_recent_searches(user_id)
    return {"success": True}


# Stats
@router.get("/stats")
async def get_index_stats():
    """Get search index statistics."""
    service = get_service()
    return await service.get_index_stats()
