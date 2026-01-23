"""API routes for operator mode and draft management."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

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


class BulkDraftItem(BaseModel):
    """Single draft for bulk loading."""
    recipient: str
    recipient_name: Optional[str] = None
    company_name: Optional[str] = None
    subject: str
    body: str
    request: Optional[str] = None  # Original request/context


class BulkLoadDraftsRequest(BaseModel):
    """Request to bulk load drafts."""
    drafts: List[BulkDraftItem]
    source: str = "bulk_import"


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


@router.get("/drafts/scored", response_model=List[Dict[str, Any]])
async def get_scored_drafts(check_hubspot: bool = True) -> List[Dict[str, Any]]:
    """Get pending drafts scored and sorted by priority.
    
    Scores leads based on:
    - Recency: Have we emailed them recently? (DEPRIORITIZE if yes)
    - ICP fit: Does their title/function match target buyers?
    - TAM fit: Is the company in our target market?
    
    Args:
        check_hubspot: Check HubSpot for email history (slower but accurate)
        
    Returns:
        List of scored drafts sorted by priority (best leads first)
    """
    try:
        from src.scoring.queue_scorer import score_pending_queue
        
        scores = await score_pending_queue(check_hubspot=check_hubspot)
        logger.info(f"Returned {len(scores)} scored drafts")
        return scores
        
    except Exception as e:
        logger.error(f"Error scoring drafts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drafts/scored/summary", response_model=Dict[str, Any])
async def get_scoring_summary(check_hubspot: bool = False) -> Dict[str, Any]:
    """Get summary of queue scoring without HubSpot check (fast).
    
    Returns tier breakdown and top leads without checking HubSpot.
    """
    try:
        from src.scoring.queue_scorer import score_pending_queue
        
        # Fast scoring without HubSpot
        scores = await score_pending_queue(check_hubspot=check_hubspot)
        
        # Calculate tier breakdown
        tiers = {"A": 0, "B": 0, "C": 0, "D": 0}
        recently_contacted = 0
        
        for s in scores:
            tiers[s.get("tier", "C")] += 1
            if s.get("recently_contacted"):
                recently_contacted += 1
        
        return {
            "total": len(scores),
            "tiers": tiers,
            "recently_contacted": recently_contacted,
            "top_10": scores[:10],
            "skip_recommended": [s for s in scores if s.get("recently_contacted")][:5],
        }
        
    except Exception as e:
        logger.error(f"Error getting scoring summary: {e}")
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
        
        # AUTO-SEND: Send email after approval (if send mode enabled)
        try:
            from src.feature_flags import get_feature_flag_service
            from src.connectors.gmail import create_gmail_connector
            from src.rate_limiter import get_rate_limiter
            
            feature_flags = get_feature_flag_service()
            
            # Check if auto-send is allowed (MODE_DRAFT_ONLY must be False)
            if feature_flags.is_send_mode_enabled():
                # Rate limit check
                rate_limiter = get_rate_limiter()
                recipient = draft.get("recipient")
                
                if await rate_limiter.check_rate_limit(f"email_send:{recipient}"):
                    # Send email via Gmail
                    gmail = create_gmail_connector()
                    message_id = await gmail.send_message(
                        to=recipient,
                        subject=draft.get("subject"),
                        body=draft.get("body")
                    )
                    
                    if message_id:
                        # Mark as sent
                        await queue.mark_sent(draft_id)
                        draft["gmail_message_id"] = message_id
                        draft["sent_at"] = datetime.utcnow().isoformat()
                        
                        logger.info(f"✅ Auto-sent email: {draft_id} → {recipient} (message_id: {message_id})")
                    else:
                        logger.error(f"Failed to send email for draft {draft_id}")
                else:
                    logger.warning(f"Rate limit hit for {recipient}, draft {draft_id} approved but not sent")
            else:
                logger.info(f"DRAFT_ONLY mode enabled - draft {draft_id} approved but not sent")
                
        except Exception as send_error:
            logger.error(f"Auto-send failed for draft {draft_id}: {send_error}")
            # Don't fail the approval - draft is still approved, just not sent yet
        
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


@router.get("/workflows", response_model=List[Dict[str, Any]])
async def get_recent_workflows(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent workflow runs."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        workflows = await db.get_recent_workflows(limit=limit)
        # Convert datetime objects to strings
        for w in workflows:
            for k, v in w.items():
                if hasattr(v, 'isoformat'):
                    w[k] = v.isoformat()
        logger.info(f"Retrieved {len(workflows)} recent workflows")
        return workflows
    except Exception as e:
        logger.error(f"Error getting workflows: {e}")
        return []


@router.post("/workflows/{workflow_id}/retry", response_model=Dict[str, Any])
async def retry_workflow(workflow_id: str) -> Dict[str, Any]:
    """Retry a failed workflow."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        
        # Get the original workflow
        workflows = await db.get_recent_workflows(limit=100)
        workflow = next((w for w in workflows if w.get("workflow_id") == workflow_id), None)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        
        if workflow.get("status") != "failed":
            raise HTTPException(status_code=400, detail=f"Can only retry failed workflows, current status: {workflow.get('status')}")
        
        # Re-trigger the workflow with the original data
        from src.formlead_orchestrator import FormLeadOrchestrator
        orchestrator = FormLeadOrchestrator()
        
        result = await orchestrator.process_formlead({
            "email": workflow.get("contact_email"),
            "company": workflow.get("company_name"),
            "formId": "workflow-trigger",  # Use workflow trigger form ID
            "formSubmissionId": f"retry-{workflow_id}",
        })
        
        logger.info(f"Retried workflow {workflow_id}, new result: {result.get('status')}")
        
        return {
            "original_workflow_id": workflow_id,
            "new_workflow_id": result.get("workflow_id"),
            "status": result.get("status"),
            "message": "Workflow retry initiated"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/stats", response_model=Dict[str, Any])
async def get_workflow_stats() -> Dict[str, Any]:
    """Get workflow statistics for dashboard."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        stats = await db.get_workflow_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting workflow stats: {e}")
        return {"today": {"total": 0, "success": 0, "failed": 0, "running": 0}}


@router.post("/bulk-load-drafts", response_model=Dict[str, Any])
async def bulk_load_drafts(request: BulkLoadDraftsRequest) -> Dict[str, Any]:
    """Bulk load drafts from external source (e.g., JSON file).
    
    This endpoint allows loading pre-generated email drafts into the 
    pending approval queue. Used for migrating drafts from local development
    or batch processing results.
    """
    try:
        queue = get_draft_queue()
        loaded = 0
        skipped = 0
        errors = []
        
        for item in request.drafts:
            try:
                # Generate unique draft ID
                draft_id = str(uuid.uuid4())
                
                # Create draft
                await queue.create_draft(
                    draft_id=draft_id,
                    recipient=item.recipient,
                    subject=item.subject,
                    body=item.body,
                    company_name=item.company_name,
                    metadata={
                        "source": request.source,
                        "recipient_name": item.recipient_name,
                        "original_request": item.request,
                    }
                )
                loaded += 1
                
                # Log progress every 50
                if loaded % 50 == 0:
                    logger.info(f"Bulk load progress: {loaded} drafts loaded")
                    
            except Exception as e:
                skipped += 1
                errors.append({"recipient": item.recipient, "error": str(e)})
                logger.warning(f"Skipped draft for {item.recipient}: {e}")
        
        logger.info(f"Bulk load complete: {loaded} loaded, {skipped} skipped")
        
        return {
            "status": "success",
            "loaded": loaded,
            "skipped": skipped,
            "total": len(request.drafts),
            "errors": errors[:10] if errors else [],  # First 10 errors only
        }
        
    except Exception as e:
        logger.error(f"Bulk load failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

