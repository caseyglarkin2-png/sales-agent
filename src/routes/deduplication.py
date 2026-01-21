"""API routes for contact deduplication."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.deduplication import (
    get_dedup_engine,
    DeduplicationRule,
    MatchConfidence,
)

router = APIRouter(prefix="/api/deduplication", tags=["deduplication"])


class FindDuplicatesRequest(BaseModel):
    contact: dict
    existing_contacts: list[dict]
    threshold: float = 70.0


class BulkDeduplicationRequest(BaseModel):
    contacts: list[dict]
    threshold: float = 70.0


class MergeContactsRequest(BaseModel):
    master_id: str
    duplicate_ids: list[str]
    contacts: dict
    merge_strategy: str = "keep_master"
    merged_by: str = "system"


class AddRuleRequest(BaseModel):
    id: str
    name: str
    field: str
    match_type: str
    weight: float = 1.0
    threshold: float = 0.8


class ResolveMatchRequest(BaseModel):
    contact_id_1: str
    contact_id_2: str
    action: str  # merge, not_duplicate, skip


@router.post("/find")
async def find_duplicates(request: FindDuplicatesRequest):
    """Find duplicates for a single contact."""
    engine = get_dedup_engine()
    
    matches = engine.find_duplicates(
        contact=request.contact,
        existing_contacts=request.existing_contacts,
        threshold=request.threshold,
    )
    
    return {
        "matches": [m.to_dict() for m in matches],
        "total": len(matches),
    }


@router.post("/bulk")
async def run_bulk_deduplication(request: BulkDeduplicationRequest):
    """Run deduplication across all contacts."""
    engine = get_dedup_engine()
    
    matches = engine.run_bulk_deduplication(
        contacts=request.contacts,
        threshold=request.threshold,
    )
    
    # Group by confidence
    by_confidence = {}
    for match in matches:
        conf = match.confidence.value
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
    
    return {
        "matches": [m.to_dict() for m in matches[:100]],  # Limit response
        "total": len(matches),
        "by_confidence": by_confidence,
    }


@router.post("/merge")
async def merge_contacts(request: MergeContactsRequest):
    """Merge duplicate contacts."""
    engine = get_dedup_engine()
    
    result = engine.merge_contacts(
        master_id=request.master_id,
        duplicate_ids=request.duplicate_ids,
        contacts=request.contacts,
        merge_strategy=request.merge_strategy,
        merged_by=request.merged_by,
    )
    
    return result.to_dict()


@router.get("/pending")
async def get_pending_matches(confidence: Optional[str] = None):
    """Get pending duplicate matches."""
    engine = get_dedup_engine()
    
    conf = None
    if confidence:
        try:
            conf = MatchConfidence(confidence)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid confidence. Valid: {[c.value for c in MatchConfidence]}"
            )
    
    matches = engine.get_pending_matches(confidence=conf)
    
    return {
        "matches": [m.to_dict() for m in matches],
        "total": len(matches),
    }


@router.post("/resolve")
async def resolve_match(request: ResolveMatchRequest):
    """Resolve a duplicate match."""
    engine = get_dedup_engine()
    
    if request.action not in ["merge", "not_duplicate", "skip"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Valid: merge, not_duplicate, skip"
        )
    
    success = engine.resolve_match(
        contact_id_1=request.contact_id_1,
        contact_id_2=request.contact_id_2,
        action=request.action,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return {"message": "Match resolved", "action": request.action}


@router.get("/rules")
async def get_rules():
    """Get all deduplication rules."""
    engine = get_dedup_engine()
    rules = engine.get_rules()
    
    return {
        "rules": [r.to_dict() for r in rules],
        "total": len(rules),
    }


@router.post("/rules")
async def add_rule(request: AddRuleRequest):
    """Add a new deduplication rule."""
    engine = get_dedup_engine()
    
    rule = DeduplicationRule(
        id=request.id,
        name=request.name,
        field=request.field,
        match_type=request.match_type,
        weight=request.weight,
        threshold=request.threshold,
    )
    
    engine.add_rule(rule)
    
    return {
        "message": "Rule added",
        "rule": rule.to_dict(),
    }


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, updates: dict):
    """Update a deduplication rule."""
    engine = get_dedup_engine()
    
    rule = engine.update_rule(rule_id, updates)
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "message": "Rule updated",
        "rule": rule.to_dict(),
    }


@router.get("/confidence-levels")
async def list_confidence_levels():
    """List all match confidence levels."""
    return {
        "levels": [
            {
                "level": conf.value,
                "name": conf.name.replace("_", " ").title(),
            }
            for conf in MatchConfidence
        ]
    }
