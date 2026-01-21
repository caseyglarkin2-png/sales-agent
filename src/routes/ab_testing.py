"""
A/B Testing Routes.

API endpoints for email A/B testing.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.testing import (
    get_ab_testing_engine,
    VariantType,
    TestStatus,
    PRESET_TESTS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ab-tests", tags=["ab-testing"])


class CreateTestRequest(BaseModel):
    name: str
    variant_type: str
    variants: List[Dict[str, str]]
    target_impressions: int = 100
    persona_filter: Optional[str] = None
    industry_filter: Optional[str] = None


class RecordEventRequest(BaseModel):
    test_id: str
    variant_id: str


@router.get("/presets")
async def get_presets() -> Dict[str, Any]:
    """Get preset test configurations."""
    return {
        "presets": [
            {
                "id": key,
                "name": preset["name"],
                "variant_type": preset["variant_type"].value,
                "variants": preset["variants"],
            }
            for key, preset in PRESET_TESTS.items()
        ],
    }


@router.post("/create")
async def create_test(request: CreateTestRequest) -> Dict[str, Any]:
    """Create a new A/B test."""
    engine = get_ab_testing_engine()
    
    try:
        variant_type = VariantType(request.variant_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid variant type: {request.variant_type}")
    
    test = engine.create_test(
        name=request.name,
        variant_type=variant_type,
        variants=request.variants,
        target_impressions=request.target_impressions,
        persona_filter=request.persona_filter,
        industry_filter=request.industry_filter,
    )
    
    return {
        "status": "success",
        "test": test.to_dict(),
    }


@router.post("/create-preset/{preset_id}")
async def create_preset_test(
    preset_id: str,
    target_impressions: int = 100,
) -> Dict[str, Any]:
    """Create a test from a preset."""
    if preset_id not in PRESET_TESTS:
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset_id}")
    
    preset = PRESET_TESTS[preset_id]
    engine = get_ab_testing_engine()
    
    test = engine.create_test(
        name=preset["name"],
        variant_type=preset["variant_type"],
        variants=preset["variants"],
        target_impressions=target_impressions,
    )
    
    return {
        "status": "success",
        "test": test.to_dict(),
    }


@router.post("/{test_id}/start")
async def start_test(test_id: str) -> Dict[str, Any]:
    """Start an A/B test."""
    engine = get_ab_testing_engine()
    
    success = engine.start_test(test_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {
        "status": "success",
        "message": f"Test {test_id} started",
    }


@router.post("/{test_id}/pause")
async def pause_test(test_id: str) -> Dict[str, Any]:
    """Pause an A/B test."""
    engine = get_ab_testing_engine()
    
    success = engine.pause_test(test_id)
    if not success:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return {
        "status": "success",
        "message": f"Test {test_id} paused",
    }


@router.get("/{test_id}")
async def get_test(test_id: str) -> Dict[str, Any]:
    """Get test details and results."""
    engine = get_ab_testing_engine()
    
    results = engine.get_test_results(test_id)
    if not results:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return results


@router.get("/{test_id}/variant/{contact_email}")
async def get_variant(test_id: str, contact_email: str) -> Dict[str, Any]:
    """Get assigned variant for a contact."""
    engine = get_ab_testing_engine()
    
    variant = engine.get_variant_for_contact(test_id, contact_email)
    if not variant:
        raise HTTPException(status_code=404, detail="Test not found or not active")
    
    return {
        "variant_id": variant.id,
        "variant_name": variant.name,
        "content": variant.content,
    }


@router.post("/record/impression")
async def record_impression(request: RecordEventRequest) -> Dict[str, Any]:
    """Record an impression (email sent)."""
    engine = get_ab_testing_engine()
    engine.record_impression(request.test_id, request.variant_id)
    return {"status": "success"}


@router.post("/record/open")
async def record_open(request: RecordEventRequest) -> Dict[str, Any]:
    """Record an email open."""
    engine = get_ab_testing_engine()
    engine.record_open(request.test_id, request.variant_id)
    return {"status": "success"}


@router.post("/record/click")
async def record_click(request: RecordEventRequest) -> Dict[str, Any]:
    """Record a link click."""
    engine = get_ab_testing_engine()
    engine.record_click(request.test_id, request.variant_id)
    return {"status": "success"}


@router.post("/record/reply")
async def record_reply(request: RecordEventRequest) -> Dict[str, Any]:
    """Record a reply."""
    engine = get_ab_testing_engine()
    engine.record_reply(request.test_id, request.variant_id)
    return {"status": "success"}


@router.post("/record/meeting")
async def record_meeting(request: RecordEventRequest) -> Dict[str, Any]:
    """Record a meeting booked."""
    engine = get_ab_testing_engine()
    engine.record_meeting(request.test_id, request.variant_id)
    return {"status": "success"}


@router.get("/")
async def list_tests(
    status: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """List all A/B tests."""
    engine = get_ab_testing_engine()
    
    status_filter = None
    if status:
        try:
            status_filter = TestStatus(status)
        except ValueError:
            pass
    
    tests = engine.list_tests(status=status_filter, limit=limit)
    
    return {
        "tests": tests,
        "count": len(tests),
    }


@router.get("/active")
async def get_active_tests() -> Dict[str, Any]:
    """Get all active tests."""
    engine = get_ab_testing_engine()
    tests = engine.get_active_tests()
    
    return {
        "tests": tests,
        "count": len(tests),
    }
