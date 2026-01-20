"""API routes for operator mode and draft management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from src.logger import get_logger
from src.operator_mode import get_draft_queue, DraftStatus
from src.rate_limiter import get_rate_limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/api/operator", tags=["operator"])


class CreateDraftRequest(BaseModel):
    """Request to create a draft."""
    recipient: str
    subject: str
    body: str
    metadata: Dict[str, Any] | None = None


class ApproveDraftRequest(BaseModel):
    """Request to approve a draft."""
    approved_by: str


class RejectDraftRequest(BaseModel):
    """Request to reject a draft."""
    reason: str
    rejected_by: str


@router.post("/drafts", response_model=Dict[str, Any])
async def create_draft(draft_id: str, request: CreateDraftRequest) -> Dict[str, Any]:
    """Create a new draft for operator review."""
    try:
        queue = get_draft_queue()
        
        # Check rate limits
        rate_limiter = get_rate_limiter()
        can_send, msg = await rate_limiter.check_can_send(request.recipient)
        if not can_send:
            raise HTTPException(status_code=429, detail=msg)
        
        draft = await queue.create_draft(
            draft_id=draft_id,
            recipient=request.recipient,
            subject=request.subject,
            body=request.body,
            metadata=request.metadata
        )
        
        logger.info(f"Draft created: {draft_id}")
        return draft
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts/pending", response_model=List[Dict[str, Any]])
async def get_pending_drafts() -> List[Dict[str, Any]]:
    """Get all drafts pending operator approval."""
    try:
        queue = get_draft_queue()
        pending = await queue.get_pending_approvals()
        logger.info(f"Retrieved {len(pending)} pending drafts")
        return pending
    except Exception as e:
        logger.error(f"Error retrieving pending drafts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts/{draft_id}", response_model=Dict[str, Any])
async def get_draft(draft_id: str) -> Dict[str, Any]:
    """Get draft details."""
    try:
        queue = get_draft_queue()
        draft = await queue.get_draft(draft_id)
        
        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
        
        return draft
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/approve", response_model=Dict[str, Any])
async def approve_draft(draft_id: str, request: ApproveDraftRequest) -> Dict[str, Any]:
    """Approve a draft for sending."""
    try:
        queue = get_draft_queue()
        success = await queue.approve_draft(draft_id, request.approved_by)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Could not approve draft: {draft_id}")
        
        draft = await queue.get_draft(draft_id)
        logger.info(f"Draft approved: {draft_id} by {request.approved_by}")
        return draft
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/reject", response_model=Dict[str, Any])
async def reject_draft(draft_id: str, request: RejectDraftRequest) -> Dict[str, Any]:
    """Reject a draft."""
    try:
        queue = get_draft_queue()
        success = await queue.reject_draft(draft_id, request.reason, request.rejected_by)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Could not reject draft: {draft_id}")
        
        draft = await queue.get_draft(draft_id)
        logger.info(f"Draft rejected: {draft_id} by {request.rejected_by}")
        return draft
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/drafts/{draft_id}/send", response_model=Dict[str, Any])
async def send_draft(draft_id: str) -> Dict[str, Any]:
    """Send an approved draft."""
    try:
        queue = get_draft_queue()
        draft = await queue.get_draft(draft_id)
        
        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft not found: {draft_id}")
        
        if draft["status"] != DraftStatus.APPROVED:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send draft with status: {draft['status']}"
            )
        
        # Record rate limit
        rate_limiter = get_rate_limiter()
        await rate_limiter.record_send(draft["recipient"])
        
        # Mark as sent
        await queue.mark_sent(draft_id)
        
        logger.info(f"Draft sent: {draft_id} to {draft['recipient']}")
        return await queue.get_draft(draft_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota/{contact_email}", response_model=Dict[str, Any])
async def get_quota(contact_email: str) -> Dict[str, Any]:
    """Get remaining email quota for a contact."""
    try:
        rate_limiter = get_rate_limiter()
        quota = await rate_limiter.get_remaining_quota(contact_email)
        return quota
    except Exception as e:
        logger.error(f"Error getting quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))
