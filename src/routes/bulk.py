"""API routes for bulk processing."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.logger import get_logger
from src.queue.bulk_processor import get_bulk_processor, RateLimitConfig
from src.scoring.lead_scorer import get_lead_scorer

logger = get_logger(__name__)

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


class BulkImportRequest(BaseModel):
    """Request to import contacts for bulk processing."""
    contacts: List[Dict[str, Any]]
    source: str = "manual_import"
    form_id: Optional[str] = None


class BulkStartRequest(BaseModel):
    """Request to start bulk processing from HubSpot form."""
    form_id: str
    limit: int = 500


class RateLimitUpdateRequest(BaseModel):
    """Request to update rate limits."""
    daily_limit: int = 20
    weekly_limit: int = 100
    hourly_limit: int = 5
    min_delay_seconds: int = 30


@router.get("/status")
async def get_bulk_status() -> Dict[str, Any]:
    """Get current bulk processing status."""
    processor = get_bulk_processor()
    stats = processor.get_stats()
    can_process, reason = processor.can_process_now()
    
    return {
        **stats.model_dump(),
        "can_process_now": can_process,
        "status_reason": reason,
        "rate_config": {
            "daily_limit": processor.rate_config.daily_limit,
            "weekly_limit": processor.rate_config.weekly_limit,
            "hourly_limit": processor.rate_config.hourly_limit,
            "min_delay_seconds": processor.rate_config.min_delay_seconds,
        }
    }


@router.post("/import")
async def import_contacts(request: BulkImportRequest) -> Dict[str, Any]:
    """Import contacts for bulk processing.
    
    Contacts should have: email, first_name, last_name, company, job_title
    """
    processor = get_bulk_processor()
    scorer = get_lead_scorer()
    
    # Score and rank leads first
    scored_leads = scorer.rank_leads(request.contacts)
    
    # Add to queue
    result = await processor.add_contacts(
        contacts=scored_leads,
        source=request.source,
        form_id=request.form_id,
    )
    
    return {
        "status": "success",
        "message": f"Imported {result['added']} contacts",
        **result,
        "top_leads": [
            {
                "email": lead["email"],
                "company": lead.get("company", ""),
                "tier": lead["tier"],
                "score": lead["total_score"],
            }
            for lead in scored_leads[:5]
        ],
    }


@router.post("/start")
async def start_bulk_from_hubspot(request: BulkStartRequest) -> Dict[str, Any]:
    """Start bulk processing from HubSpot form submissions."""
    try:
        from src.connectors.hubspot import create_hubspot_connector
        
        hubspot = create_hubspot_connector()
        
        # Fetch form submissions
        logger.info(f"Fetching form submissions for {request.form_id}")
        submissions = await hubspot.get_form_submissions(
            form_id=request.form_id,
            limit=request.limit,
        )
        
        if not submissions:
            return {
                "status": "warning",
                "message": f"No submissions found for form {request.form_id}",
                "submissions_found": 0,
            }
        
        # Convert to contact format
        contacts = []
        for sub in submissions:
            contacts.append({
                "email": sub.get("email", ""),
                "first_name": sub.get("first_name", ""),
                "last_name": sub.get("last_name", ""),
                "company": sub.get("company", ""),
                "job_title": sub.get("job_title", ""),
            })
        
        # Score and import
        processor = get_bulk_processor()
        scorer = get_lead_scorer()
        
        scored_leads = scorer.rank_leads(contacts)
        result = await processor.add_contacts(
            contacts=scored_leads,
            source="hubspot_form",
            form_id=request.form_id,
        )
        
        return {
            "status": "success",
            "message": f"Queued {result['added']} contacts from form submissions",
            "form_id": request.form_id,
            **result,
        }
        
    except Exception as e:
        logger.error(f"Error starting bulk from HubSpot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-one")
async def process_one_contact() -> Dict[str, Any]:
    """Manually trigger processing of one contact."""
    from src.orchestrator import get_orchestrator
    
    processor = get_bulk_processor()
    
    can_process, reason = processor.can_process_now()
    if not can_process:
        return {
            "status": "skipped",
            "reason": reason,
        }
    
    try:
        orchestrator = get_orchestrator()
        result = await processor.process_one(orchestrator)
        
        if result:
            return result
        else:
            return {
                "status": "skipped",
                "reason": "No contacts to process or rate limited",
            }
    except Exception as e:
        logger.error(f"Error processing contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_processing() -> Dict[str, Any]:
    """Pause bulk processing."""
    processor = get_bulk_processor()
    processor.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume_processing() -> Dict[str, Any]:
    """Resume bulk processing."""
    processor = get_bulk_processor()
    processor.resume()
    return {"status": "resumed"}


@router.get("/queue")
async def get_queue() -> Dict[str, Any]:
    """Get current queue contents."""
    processor = get_bulk_processor()
    
    queue_items = list(processor.queue)[:50]  # Limit to 50 for display
    
    return {
        "total_queued": len(processor.queue),
        "showing": len(queue_items),
        "contacts": [
            {
                "email": c.email,
                "company": c.company,
                "job_title": c.job_title,
                "priority_score": c.priority_score,
                "status": c.status.value,
                "queued_at": c.queued_at.isoformat() if c.queued_at else None,
            }
            for c in queue_items
        ],
    }


@router.delete("/queue")
async def clear_queue() -> Dict[str, Any]:
    """Clear the processing queue."""
    processor = get_bulk_processor()
    count = len(processor.queue)
    processor.queue.clear()
    
    return {
        "status": "cleared",
        "contacts_removed": count,
    }


@router.put("/rate-limits")
async def update_rate_limits(request: RateLimitUpdateRequest) -> Dict[str, Any]:
    """Update rate limiting configuration."""
    processor = get_bulk_processor()
    
    processor.rate_config = RateLimitConfig(
        daily_limit=request.daily_limit,
        weekly_limit=request.weekly_limit,
        hourly_limit=request.hourly_limit,
        min_delay_seconds=request.min_delay_seconds,
    )
    
    return {
        "status": "updated",
        "rate_config": processor.rate_config.model_dump(),
    }


@router.post("/score")
async def score_leads(contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Score a list of leads without adding to queue."""
    scorer = get_lead_scorer()
    scored_leads = scorer.rank_leads(contacts)
    
    return {
        "status": "success",
        "count": len(scored_leads),
        "leads": [
            {
                "email": lead["email"],
                "company": lead.get("company", ""),
                "job_title": lead.get("job_title", ""),
                "tier": lead["tier"],
                "total_score": lead["total_score"],
                "score_breakdown": lead["score"],
            }
            for lead in scored_leads
        ],
    }
