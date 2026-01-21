"""
Segmentation API Routes
=======================
Endpoints for managing contact segments.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import structlog

from src.segmentation import get_segmentation_engine

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/segmentation", tags=["Segmentation"])


class CreateSegmentRequest(BaseModel):
    name: str
    description: str = ""
    match_type: str = "all"
    is_dynamic: bool = True


class UpdateSegmentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    match_type: Optional[str] = None
    is_dynamic: Optional[bool] = None
    is_active: Optional[bool] = None


class AddRuleRequest(BaseModel):
    field: str
    operator: str
    value: Any = None


class EvaluateContactRequest(BaseModel):
    contact: dict
    segment_id: Optional[str] = None


class GetContactsRequest(BaseModel):
    segment_id: str
    contacts: list[dict]


class PreviewSegmentRequest(BaseModel):
    rules: list[dict]
    match_type: str = "all"
    contacts: list[dict]
    limit: int = 10


@router.get("/segments")
async def list_segments(active_only: bool = True):
    """List all segments."""
    engine = get_segmentation_engine()
    segments = engine.list_segments(active_only=active_only)
    
    return {
        "segments": [s.to_dict() for s in segments],
        "total": len(segments),
    }


@router.post("/segments")
async def create_segment(request: CreateSegmentRequest):
    """Create a new segment."""
    engine = get_segmentation_engine()
    
    # Check if name already exists
    existing = engine.get_segment_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Segment with name '{request.name}' already exists",
        )
    
    segment = engine.create_segment(
        name=request.name,
        description=request.description,
        match_type=request.match_type,
        is_dynamic=request.is_dynamic,
    )
    
    logger.info("segment_created_via_api", segment_id=segment.id)
    
    return {
        "message": "Segment created",
        "segment": segment.to_dict(),
    }


@router.get("/segments/{segment_id}")
async def get_segment(segment_id: str):
    """Get a segment by ID."""
    engine = get_segmentation_engine()
    segment = engine.get_segment(segment_id)
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return {"segment": segment.to_dict()}


@router.put("/segments/{segment_id}")
async def update_segment(segment_id: str, request: UpdateSegmentRequest):
    """Update a segment."""
    engine = get_segmentation_engine()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    segment = engine.update_segment(segment_id, updates)
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return {
        "message": "Segment updated",
        "segment": segment.to_dict(),
    }


@router.delete("/segments/{segment_id}")
async def delete_segment(segment_id: str):
    """Delete a segment."""
    engine = get_segmentation_engine()
    
    if not engine.delete_segment(segment_id):
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return {"message": "Segment deleted"}


@router.post("/segments/{segment_id}/rules")
async def add_rule(segment_id: str, request: AddRuleRequest):
    """Add a rule to a segment."""
    engine = get_segmentation_engine()
    
    rule = engine.add_rule_to_segment(
        segment_id=segment_id,
        field=request.field,
        operator=request.operator,
        value=request.value,
    )
    
    if not rule:
        raise HTTPException(
            status_code=400,
            detail="Failed to add rule. Check segment ID and operator.",
        )
    
    return {
        "message": "Rule added",
        "rule": rule.to_dict(),
    }


@router.delete("/segments/{segment_id}/rules/{rule_id}")
async def remove_rule(segment_id: str, rule_id: str):
    """Remove a rule from a segment."""
    engine = get_segmentation_engine()
    
    if not engine.remove_rule_from_segment(segment_id, rule_id):
        raise HTTPException(
            status_code=404,
            detail="Segment or rule not found",
        )
    
    return {"message": "Rule removed"}


@router.post("/evaluate")
async def evaluate_contact(request: EvaluateContactRequest):
    """Evaluate which segments a contact belongs to."""
    engine = get_segmentation_engine()
    
    results = engine.evaluate_contact(
        contact=request.contact,
        segment_id=request.segment_id,
    )
    
    return {
        "contact_id": request.contact.get("id"),
        "segments": results,
        "matched_count": sum(1 for v in results.values() if v),
    }


@router.post("/contacts")
async def get_contacts_in_segment(request: GetContactsRequest):
    """Get contacts that match a segment."""
    engine = get_segmentation_engine()
    
    matching = engine.get_contacts_in_segment(
        segment_id=request.segment_id,
        contacts=request.contacts,
    )
    
    return {
        "segment_id": request.segment_id,
        "matching_contacts": matching,
        "total": len(matching),
    }


@router.get("/segments/{segment_id}/stats")
async def get_segment_stats(segment_id: str):
    """Get statistics for a segment."""
    engine = get_segmentation_engine()
    
    stats = engine.get_segment_stats(segment_id)
    
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    
    return stats


@router.post("/segments/{segment_id}/refresh")
async def refresh_membership(segment_id: str, contacts: list[dict]):
    """Refresh segment membership for all contacts."""
    engine = get_segmentation_engine()
    
    result = engine.refresh_segment_membership(
        segment_id=segment_id,
        contacts=contacts,
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/preview")
async def preview_segment(request: PreviewSegmentRequest):
    """Preview segment membership without creating it."""
    engine = get_segmentation_engine()
    
    result = engine.preview_segment(
        rules=request.rules,
        match_type=request.match_type,
        contacts=request.contacts,
        limit=request.limit,
    )
    
    return result


@router.get("/operators")
async def list_operators():
    """List available rule operators."""
    from src.segmentation.segmentation_engine import RuleOperator
    
    operators = [
        {"value": op.value, "name": op.name}
        for op in RuleOperator
    ]
    
    return {"operators": operators}
