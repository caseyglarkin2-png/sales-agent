"""
LinkedIn Outreach Routes.

API endpoints for managing LinkedIn outreach queue.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.outreach import get_linkedin_manager, LinkedInActionType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


class CreateConnectionRequest(BaseModel):
    contact_email: str
    contact_name: str
    company: str
    job_title: str
    linkedin_url: Optional[str] = None
    persona: Optional[str] = None
    custom_message: Optional[str] = None


class CreateMessageRequest(BaseModel):
    contact_email: str
    contact_name: str
    message: str
    linkedin_url: Optional[str] = None


class CompleteActionRequest(BaseModel):
    action_id: str
    notes: Optional[str] = None


@router.get("/queue")
async def get_queue(
    limit: int = 20,
    action_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Get pending LinkedIn actions."""
    manager = get_linkedin_manager()
    
    type_filter = None
    if action_type:
        try:
            type_filter = LinkedInActionType(action_type)
        except ValueError:
            pass
    
    actions = manager.get_pending_actions(limit=limit, action_type=type_filter)
    
    return {
        "actions": actions,
        "total": len(actions),
    }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get LinkedIn outreach statistics."""
    manager = get_linkedin_manager()
    return manager.get_stats()


@router.get("/daily-batch")
async def get_daily_batch(limit: int = 20) -> Dict[str, Any]:
    """Get today's batch of LinkedIn actions to execute."""
    manager = get_linkedin_manager()
    batch = manager.generate_daily_batch(limit=limit)
    
    return {
        "batch": batch,
        "count": len(batch),
        "recommended_limit": 20,
    }


@router.post("/connection-request")
async def create_connection_request(request: CreateConnectionRequest) -> Dict[str, Any]:
    """Create a LinkedIn connection request."""
    manager = get_linkedin_manager()
    
    action = manager.create_connection_request(
        contact_email=request.contact_email,
        contact_name=request.contact_name,
        company=request.company,
        job_title=request.job_title,
        linkedin_url=request.linkedin_url,
        persona=request.persona,
        custom_message=request.custom_message,
    )
    
    return {
        "status": "success",
        "action": action.to_dict(),
    }


@router.post("/message")
async def create_message(request: CreateMessageRequest) -> Dict[str, Any]:
    """Create a LinkedIn direct message."""
    manager = get_linkedin_manager()
    
    action = manager.create_message(
        contact_email=request.contact_email,
        contact_name=request.contact_name,
        message=request.message,
        linkedin_url=request.linkedin_url,
    )
    
    return {
        "status": "success",
        "action": action.to_dict(),
    }


@router.post("/complete")
async def complete_action(request: CompleteActionRequest) -> Dict[str, Any]:
    """Mark a LinkedIn action as completed."""
    manager = get_linkedin_manager()
    
    success = manager.mark_completed(
        action_id=request.action_id,
        notes=request.notes,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return {
        "status": "success",
        "message": f"Action {request.action_id} marked as completed",
    }


@router.post("/skip")
async def skip_action(action_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Skip a LinkedIn action."""
    manager = get_linkedin_manager()
    
    success = manager.mark_skipped(
        action_id=action_id,
        reason=reason,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return {
        "status": "success",
        "message": f"Action {action_id} skipped",
    }


@router.post("/bulk-create")
async def bulk_create_connections(
    contacts: list[Dict[str, Any]],
    persona: Optional[str] = None,
) -> Dict[str, Any]:
    """Bulk create connection requests."""
    manager = get_linkedin_manager()
    created = 0
    
    for contact in contacts:
        try:
            manager.create_connection_request(
                contact_email=contact.get("email", ""),
                contact_name=contact.get("name", ""),
                company=contact.get("company", ""),
                job_title=contact.get("job_title", ""),
                linkedin_url=contact.get("linkedin_url"),
                persona=persona or contact.get("persona"),
            )
            created += 1
        except Exception as e:
            logger.warning(f"Could not create connection for {contact.get('email')}: {e}")
    
    return {
        "status": "success",
        "created": created,
        "total": len(contacts),
    }
