"""GDPR Data Deletion Routes.

Endpoints for:
- User data deletion requests (right to be forgotten)
- GDPR compliance queries
- Data export requests (future: DSAR - Data Subject Access Request)
"""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from src.logger import get_logger
from src.gdpr import get_gdpr_service
from src.security.auth import require_admin_role
from src.rate_limiter import rate_limit

logger = get_logger(__name__)

router = APIRouter(prefix="/api/gdpr", tags=["GDPR & Data Privacy"])


# ===== Request/Response Models =====

class GDPRDeleteRequest(BaseModel):
    """Request to delete user data."""
    email: EmailStr
    reason: Optional[str] = Field(
        default="User requested data deletion",
        description="Reason for deletion request"
    )
    verify_email: Optional[str] = Field(
        default=None,
        description="Email confirmation (must match email field)"
    )


class GDPRDeleteResponse(BaseModel):
    """Response from data deletion request."""
    status: str = "success"
    message: str
    email: str
    timestamp: str
    request_id: str
    deleted_records: Dict[str, int]
    next_steps: str


class GDPRDeleteUserRequest(BaseModel):
    """Admin request to delete specific user data."""
    reason: Optional[str] = Field(
        default="Administrative deletion",
        description="Reason for admin-initiated deletion"
    )


class DataRetentionPolicy(BaseModel):
    """Data retention policy information."""
    drafts_retention_days: int = 90
    audit_trail_retention_years: int = 1
    email_bodies_retention_days: int = 30
    archival_enabled: bool = True


# ===== Public GDPR Routes =====

@router.get("/policy", response_model=DataRetentionPolicy)
async def get_retention_policy() -> DataRetentionPolicy:
    """Get the organization's data retention policy."""
    return DataRetentionPolicy(
        drafts_retention_days=90,
        audit_trail_retention_years=1,
        email_bodies_retention_days=30,
        archival_enabled=True,
    )


@router.post("/delete-request", response_model=GDPRDeleteResponse)
@rate_limit(max_requests=1, window_seconds=3600)  # Max 1 per hour per IP
async def request_data_deletion(
    request: GDPRDeleteRequest,
    http_request: Request = None
) -> GDPRDeleteResponse:
    """
    Request deletion of all personal data (right to be forgotten).
    
    User must verify email match as confirmation mechanism.
    
    Args:
        request: Deletion request with email and verification
        
    Returns:
        Confirmation of deletion request
        
    Note:
        - User must provide verify_email matching the email field
        - Deletion is asynchronous and logged for audit trail
        - Some data (audit trail) is preserved for 1 year for legal compliance
    """
    # Verify email confirmation
    if request.verify_email != request.email:
        logger.warning(
            "GDPR deletion requested with mismatched verification",
            email=request.email,
        )
        raise HTTPException(
            status_code=400,
            detail="Email verification mismatch. verify_email must match email.",
        )

    try:
        gdpr_service = get_gdpr_service()
        
        # Get client IP for logging
        client_ip = http_request.client.host if http_request and http_request.client else "unknown"
        
        # Generate request ID for tracking
        import uuid
        request_id = str(uuid.uuid4())

        logger.info(
            "GDPR deletion request received",
            email=request.email,
            request_id=request_id,
            client_ip=client_ip,
        )

        # Perform deletion
        stats = await gdpr_service.delete_user_data(
            email=request.email,
            reason=request.reason or "User requested via GDPR endpoint",
        )

        return GDPRDeleteResponse(
            status="success",
            message=f"Your data deletion request has been processed. "
                   f"All personal information has been removed from our systems.",
            email=request.email,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            deleted_records=stats["deleted_records"],
            next_steps="You will receive a confirmation email within 24 hours. "
                      "Our audit trail retention (1 year) complies with GDPR regulations.",
        )

    except Exception as e:
        logger.error(
            "GDPR deletion request failed",
            email=request.email,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process deletion request. Please contact support.",
        )


# ===== Admin-Only GDPR Routes =====

@router.delete("/user/{email}", response_model=GDPRDeleteResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_user_data(
    email: str,
    reason: Optional[str] = Query(
        default="Administrative deletion",
        description="Reason for deletion"
    ),
    http_request: Request = None
) -> GDPRDeleteResponse:
    """
    Admin endpoint to delete all data for a user.
    
    Requires: X-Admin-Token header
    
    Args:
        email: User email to delete
        reason: Reason for deletion
        
    Returns:
        Deletion statistics and confirmation
        
    Note:
        - Requires admin authentication via X-Admin-Token header
        - Deletion is logged with admin ID and reason
        - Cannot be undone without database restore
    """
    # Verify admin role
    await require_admin_role(http_request)

    try:
        gdpr_service = get_gdpr_service()
        
        # Extract admin ID from request if available
        admin_id = http_request.headers.get("X-Admin-ID", "unknown")
        
        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())

        logger.info(
            "Admin GDPR deletion initiated",
            email=email,
            admin_id=admin_id,
            request_id=request_id,
        )

        # Perform deletion
        stats = await gdpr_service.delete_user_data(
            email=email,
            admin_id=admin_id,
            reason=reason,
        )

        logger.info(
            "Admin GDPR deletion completed",
            email=email,
            deleted_count=sum(stats["deleted_records"].values()),
        )

        return GDPRDeleteResponse(
            status="success",
            message=f"User data for {email} has been deleted successfully.",
            email=email,
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id,
            deleted_records=stats["deleted_records"],
            next_steps=f"Deletion logged with ID {request_id}. Audit trail preserved for 1 year.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Admin GDPR deletion failed",
            email=email,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete user data: {str(e)}",
        )


@router.post("/cleanup-old-drafts")
async def trigger_cleanup_old_drafts(
    days_old: int = Query(
        default=90,
        ge=1,
        le=365,
        description="Delete drafts older than this many days"
    ),
    dry_run: bool = Query(
        default=True,
        description="If true, report what would be deleted without deleting"
    ),
    http_request: Request = None
) -> Dict[str, Any]:
    """
    Admin endpoint to cleanup old draft emails.
    
    Requires: X-Admin-Token header
    
    Args:
        days_old: Delete drafts older than this many days (default: 90)
        dry_run: If true, report without deleting (default: true for safety)
        
    Returns:
        Cleanup statistics
        
    Note:
        - Default dry_run=true for safety
        - Set dry_run=false to actually delete
        - Approved drafts are preserved regardless
    """
    # Verify admin role
    await require_admin_role(http_request)

    try:
        gdpr_service = get_gdpr_service()

        logger.info(
            "Draft cleanup requested",
            days_old=days_old,
            dry_run=dry_run,
        )

        stats = await gdpr_service.cleanup_old_drafts(
            days_old=days_old,
            dry_run=dry_run,
        )

        if dry_run:
            stats["warning"] = "This was a dry run. Set dry_run=false to actually delete."

        return stats

    except Exception as e:
        logger.error("Draft cleanup failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}",
        )


@router.post("/anonymize-old-records")
async def trigger_anonymize_old_records(
    days_old: int = Query(
        default=365,
        ge=1,
        le=3650,
        description="Anonymize records older than this many days"
    ),
    dry_run: bool = Query(
        default=True,
        description="If true, report what would be anonymized without changing"
    ),
    http_request: Request = None
) -> Dict[str, Any]:
    """
    Admin endpoint to anonymize old records.
    
    Requires: X-Admin-Token header
    
    Args:
        days_old: Anonymize records older than this many days (default: 365)
        dry_run: If true, report without anonymizing (default: true for safety)
        
    Returns:
        Anonymization statistics
        
    Note:
        - Default dry_run=true for safety
        - Replaces PII with anonymized versions
        - Audit trail is preserved
    """
    # Verify admin role
    await require_admin_role(http_request)

    try:
        gdpr_service = get_gdpr_service()

        logger.info(
            "Anonymization requested",
            days_old=days_old,
            dry_run=dry_run,
        )

        stats = await gdpr_service.anonymize_old_records(
            days_old=days_old,
            dry_run=dry_run,
        )

        if dry_run:
            stats["warning"] = "This was a dry run. Set dry_run=false to actually anonymize."

        return stats

    except Exception as e:
        logger.error("Anonymization failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Anonymization failed: {str(e)}",
        )


# ===== Health/Status Endpoints =====

@router.get("/status", response_model=Dict[str, Any])
async def get_gdpr_status() -> Dict[str, Any]:
    """Get GDPR system status."""
    return {
        "status": "operational",
        "version": "1.0",
        "features": {
            "user_deletion": True,
            "draft_cleanup": True,
            "anonymization": True,
            "audit_logging": True,
        },
        "compliance": {
            "gdpr": "Compliant",
            "audit_trail_years": 1,
            "draft_retention_days": 90,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
