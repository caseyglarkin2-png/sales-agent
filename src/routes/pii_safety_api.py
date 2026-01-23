"""
PII detection and safety validation API endpoints.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from src.pii_detector import PIIDetector, PIISafetyValidator
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/safety", tags=["safety", "pii"])


class PIIDetectionRequest(BaseModel):
    """Request for PII detection."""
    content: str
    include_positions: bool = False
    redact: bool = False


class PIIValidationRequest(BaseModel):
    """Request for safety validation."""
    content: str
    context: str = "email"
    strict_mode: bool = False


@router.post("/detect-pii")
async def detect_pii(request: PIIDetectionRequest):
    """
    Detect PII in content.
    
    Returns detected PII types and optionally redacted content.
    """
    try:
        detector = PIIDetector()
        
        # Detect PII
        detected = detector.detect(request.content, include_positions=request.include_positions)
        
        # Optionally redact
        redacted_content = None
        redaction_map = None
        if request.redact:
            redacted_content, redaction_map = detector.redact(request.content, partial=True)
        
        return {
            "pii_detected": {k.value: v for k, v in detected.items()},
            "has_pii": len(detected) > 0,
            "redacted_content": redacted_content,
            "redaction_map": {k.value: v for k, v in redaction_map.items()} if redaction_map else None,
        }
        
    except Exception as e:
        logger.error(f"PII detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PII detection failed: {str(e)}"
        )


@router.post("/validate-safety")
async def validate_safety(request: PIIValidationRequest):
    """
    Validate content safety before sending.
    
    Returns safety assessment with warnings and recommendations.
    """
    try:
        validator = PIISafetyValidator(strict_mode=request.strict_mode)
        result = validator.validate(request.content, context=request.context)
        
        return result
        
    except Exception as e:
        logger.error(f"Safety validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety validation failed: {str(e)}"
        )
