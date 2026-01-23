"""
Campaign Routes.

API endpoints for campaign management and generation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.campaigns import (
    get_campaign_manager,
    CampaignStatus,
    CampaignType,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CreateCampaignRequest(BaseModel):
    name: str
    campaign_type: str
    target_personas: List[str]
    target_industries: Optional[List[str]] = None
    target_companies: Optional[List[str]] = None
    sequence_id: Optional[str] = None
    template_ids: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None


class AddContactsRequest(BaseModel):
    contacts: List[str]


class RecordEventRequest(BaseModel):
    campaign_id: str
    count: int = 1


class GenerateCampaignRequest(BaseModel):
    """Request to generate campaign emails for a segment."""
    segment: str = Field(..., description="Segment name: chainge, high_value, engaged, cold, all")
    limit: int = Field(50, description="Maximum number of drafts to generate", ge=1, le=500)
    auto_queue: bool = Field(True, description="Automatically queue drafts for approval")
    batch_size: int = Field(10, description="Batch size for concurrent generation", ge=1, le=50)


class GenerateCustomCampaignRequest(BaseModel):
    """Request to generate campaign emails for custom contact list."""
    contacts: List[Dict[str, Any]] = Field(..., description="List of contact dictionaries")
    segment_name: Optional[str] = Field(None, description="Optional segment name for template selection")
    auto_queue: bool = Field(True, description="Automatically queue drafts for approval")
    batch_size: int = Field(10, description="Batch size for concurrent generation", ge=1, le=50)


@router.get("/types")
async def get_types() -> Dict[str, Any]:
    """Get available campaign types."""
    return {
        "types": [
            {"id": t.value, "name": t.value.replace("_", " ").title()}
            for t in CampaignType
        ],
    }


@router.get("/")
async def list_campaigns(
    status: Optional[str] = None,
    campaign_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """List all campaigns."""
    manager = get_campaign_manager()
    
    status_filter = None
    type_filter = None
    
    if status:
        try:
            status_filter = CampaignStatus(status)
        except ValueError:
            pass
    
    if campaign_type:
        try:
            type_filter = CampaignType(campaign_type)
        except ValueError:
            pass
    
    campaigns = manager.list_campaigns(
        status=status_filter,
        campaign_type=type_filter,
        limit=limit,
    )
    
    return {
        "campaigns": campaigns,
        "count": len(campaigns),
    }


@router.get("/active")
async def get_active() -> Dict[str, Any]:
    """Get active campaigns."""
    manager = get_campaign_manager()
    campaigns = manager.get_active_campaigns()
    
    return {
        "campaigns": campaigns,
        "count": len(campaigns),
    }


@router.get("/performance")
async def get_performance() -> Dict[str, Any]:
    """Get aggregate campaign performance."""
    manager = get_campaign_manager()
    return manager.get_campaign_performance()


@router.post("/")
async def create_campaign(request: CreateCampaignRequest) -> Dict[str, Any]:
    """Create a new campaign."""
    manager = get_campaign_manager()
    
    try:
        campaign_type = CampaignType(request.campaign_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid campaign type: {request.campaign_type}")
    
    start_date = None
    end_date = None
    
    if request.start_date:
        try:
            start_date = datetime.fromisoformat(request.start_date)
        except ValueError:
            pass
    
    if request.end_date:
        try:
            end_date = datetime.fromisoformat(request.end_date)
        except ValueError:
            pass
    
    campaign = manager.create_campaign(
        name=request.name,
        campaign_type=campaign_type,
        target_personas=request.target_personas,
        target_industries=request.target_industries,
        target_companies=request.target_companies,
        sequence_id=request.sequence_id,
        template_ids=request.template_ids,
        start_date=start_date,
        end_date=end_date,
        description=request.description,
        owner=request.owner,
        tags=request.tags,
    )
    
    return {
        "status": "success",
        "campaign": campaign.to_dict(),
    }


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str) -> Dict[str, Any]:
    """Get campaign details."""
    manager = get_campaign_manager()
    campaign = manager.get_campaign(campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "campaign": campaign,
    }


@router.post("/{campaign_id}/contacts")
async def add_contacts(campaign_id: str, request: AddContactsRequest) -> Dict[str, Any]:
    """Add contacts to a campaign."""
    manager = get_campaign_manager()
    
    added = manager.add_contacts(campaign_id, request.contacts)
    
    if added == 0 and campaign_id not in manager.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "status": "success",
        "added": added,
    }


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str) -> Dict[str, Any]:
    """Start a campaign."""
    manager = get_campaign_manager()
    
    success = manager.start_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot start campaign")
    
    return {
        "status": "success",
        "message": f"Campaign {campaign_id} started",
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str) -> Dict[str, Any]:
    """Pause a campaign."""
    manager = get_campaign_manager()
    
    success = manager.pause_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause campaign")
    
    return {
        "status": "success",
        "message": f"Campaign {campaign_id} paused",
    }


@router.post("/{campaign_id}/complete")
async def complete_campaign(campaign_id: str) -> Dict[str, Any]:
    """Mark campaign as completed."""
    manager = get_campaign_manager()
    
    success = manager.complete_campaign(campaign_id)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return {
        "status": "success",
        "message": f"Campaign {campaign_id} completed",
    }


@router.post("/record/send")
async def record_send(request: RecordEventRequest) -> Dict[str, Any]:
    """Record emails sent."""
    manager = get_campaign_manager()
    manager.record_send(request.campaign_id, request.count)
    return {"status": "success"}


@router.post("/record/open")
async def record_open(request: RecordEventRequest) -> Dict[str, Any]:
    """Record email opens."""
    manager = get_campaign_manager()
    manager.record_open(request.campaign_id, request.count)
    return {"status": "success"}


@router.post("/record/reply")
async def record_reply(request: RecordEventRequest) -> Dict[str, Any]:
    """Record replies."""
    manager = get_campaign_manager()
    manager.record_reply(request.campaign_id, request.count)
    return {"status": "success"}


@router.post("/record/meeting")
async def record_meeting(request: RecordEventRequest) -> Dict[str, Any]:
    """Record meetings booked."""
    manager = get_campaign_manager()
    manager.record_meeting(request.campaign_id, request.count)
    return {"status": "success"}


# ============================================================================
# Campaign Generation Endpoints
# ============================================================================


@router.post("/generate")
async def generate_campaign(
    request: GenerateCampaignRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Generate personalized email drafts for a contact segment.
    
    This endpoint:
    1. Fetches contacts from the specified segment (CHAINge, High Value, Engaged, Cold, All)
    2. Generates personalized email drafts using AI
    3. Queues drafts for operator approval
    4. Returns campaign statistics
    
    Segments:
    - chainge: CHAINge NA attendees (partnership/networking focused)
    - high_value: Enterprise contacts (ROI/revenue focused)
    - engaged: Active contacts (follow-up focused)
    - cold: Inactive contacts (re-engagement focused)
    - all: All contacts
    
    Example:
        POST /api/campaigns/generate
        {
            "segment": "chainge",
            "limit": 50,
            "auto_queue": true,
            "batch_size": 10
        }
        
        Response:
        {
            "status": "success",
            "drafts_created": 50,
            "queued_for_approval": 50,
            "errors": 0,
            "contacts_processed": 50,
            "segment": "chainge",
            "duration_seconds": 45.2
        }
    """
    try:
        from src.campaigns.campaign_generator import create_campaign_generator
        
        logger.info(f"Campaign generation requested: segment={request.segment}, limit={request.limit}")
        
        # Validate segment
        valid_segments = ["chainge", "high_value", "engaged", "cold", "all"]
        if request.segment not in valid_segments:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid segment '{request.segment}'. Must be one of: {', '.join(valid_segments)}"
            )
        
        # Create campaign generator
        generator = create_campaign_generator()
        
        # Generate campaign
        result = await generator.generate_for_segment(
            segment_name=request.segment,
            limit=request.limit,
            auto_queue=request.auto_queue,
            batch_size=request.batch_size
        )
        
        logger.info(
            f"Campaign generation completed: {result['drafts_created']} drafts, "
            f"{result['errors']} errors, segment={request.segment}"
        )
        
        return {
            "status": "success",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Campaign generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Campaign generation failed: {str(e)}"
        )


@router.post("/generate/custom")
async def generate_custom_campaign(
    request: GenerateCustomCampaignRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Generate personalized email drafts for a custom contact list.
    
    This endpoint allows you to provide a custom list of contacts instead of
    using pre-defined segments. Useful for targeted campaigns or custom lists.
    
    Example:
        POST /api/campaigns/generate/custom
        {
            "contacts": [
                {
                    "email": "john@example.com",
                    "firstname": "John",
                    "lastname": "Doe",
                    "company": "Example Corp",
                    "jobtitle": "CEO",
                    "hubspot_id": "12345"
                },
                ...
            ],
            "segment_name": "high_value",
            "auto_queue": true,
            "batch_size": 10
        }
        
        Response:
        {
            "status": "success",
            "drafts_created": 25,
            "queued_for_approval": 25,
            "errors": 0,
            "contacts_processed": 25,
            "segment": "custom_list",
            "duration_seconds": 22.1
        }
    """
    try:
        from src.campaigns.campaign_generator import create_campaign_generator
        
        logger.info(f"Custom campaign generation requested: {len(request.contacts)} contacts")
        
        if not request.contacts:
            raise HTTPException(
                status_code=400,
                detail="Contact list cannot be empty"
            )
        
        if len(request.contacts) > 500:
            raise HTTPException(
                status_code=400,
                detail="Contact list too large (max 500 contacts per request)"
            )
        
        # Validate contacts have required fields
        for i, contact in enumerate(request.contacts):
            if not contact.get("email"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Contact at index {i} missing required 'email' field"
                )
        
        # Create campaign generator
        generator = create_campaign_generator()
        
        # Generate campaign
        result = await generator.generate_for_contacts(
            contact_list=request.contacts,
            segment_name=request.segment_name,
            auto_queue=request.auto_queue,
            batch_size=request.batch_size
        )
        
        logger.info(
            f"Custom campaign generation completed: {result['drafts_created']} drafts, "
            f"{result['errors']} errors"
        )
        
        return {
            "status": "success",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom campaign generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Custom campaign generation failed: {str(e)}"
        )


@router.get("/generate/segments")
async def get_available_segments() -> Dict[str, Any]:
    """
    Get available contact segments for campaign generation.
    
    Returns information about each segment including:
    - Segment name and description
    - Number of contacts in each segment
    - Template type used for the segment
    
    Example:
        GET /api/campaigns/generate/segments
        
        Response:
        {
            "segments": [
                {
                    "name": "chainge",
                    "description": "CHAINge NA attendees",
                    "contact_count": 42,
                    "template": "partnership_networking"
                },
                ...
            ]
        }
    """
    try:
        from src.hubspot_sync import get_sync_service
        
        sync_service = get_sync_service()
        
        segments = [
            {
                "name": "chainge",
                "description": "CHAINge NA attendees - Partnership/networking focused emails",
                "template": "partnership_networking",
                "contact_count": len(sync_service.get_contacts(segment="chainge", limit=10000)["contacts"])
            },
            {
                "name": "high_value",
                "description": "High-value enterprise contacts - ROI/revenue focused emails",
                "template": "enterprise_roi",
                "contact_count": len(sync_service.get_contacts(segment="high_value", limit=10000)["contacts"])
            },
            {
                "name": "engaged",
                "description": "Recently active contacts - Follow-up and continuation emails",
                "template": "engaged_followup",
                "contact_count": len(sync_service.get_contacts(segment="engaged", limit=10000)["contacts"])
            },
            {
                "name": "cold",
                "description": "Inactive contacts - Re-engagement and reconnection emails",
                "template": "reengagement",
                "contact_count": len(sync_service.get_contacts(segment="cold", limit=10000)["contacts"])
            },
            {
                "name": "all",
                "description": "All contacts - Generic outreach emails",
                "template": "generic_outreach",
                "contact_count": len(sync_service.get_contacts(segment=None, limit=10000)["contacts"])
            }
        ]
        
        return {
            "segments": segments,
            "total_segments": len(segments)
        }
        
    except Exception as e:
        logger.error(f"Failed to get segment info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get segment information: {str(e)}"
        )


@router.get("/generate/queue")
async def get_campaign_queue() -> Dict[str, Any]:
    """
    Get status of the campaign draft approval queue.
    
    Returns all drafts pending operator approval from recent campaign generations.
    
    Example:
        GET /api/campaigns/generate/queue
        
        Response:
        {
            "total_pending": 125,
            "by_segment": {
                "chainge": 50,
                "high_value": 40,
                "engaged": 20,
                "cold": 15
            },
            "drafts": [
                {
                    "id": "draft-123",
                    "recipient": "john@example.com",
                    "subject": "Re: CHAINge NA — Partnership Opportunity",
                    "status": "PENDING_APPROVAL",
                    "created_at": "2026-01-23T10:30:00Z",
                    "metadata": {
                        "segment": "chainge",
                        "campaign": "chainge_campaign_20260123"
                    }
                },
                ...
            ]
        }
    """
    try:
        from src.operator_mode import get_draft_queue
        
        draft_queue = get_draft_queue()
        pending = await draft_queue.get_pending_approvals()
        
        # Categorize by segment
        by_segment: Dict[str, int] = {}
        for draft in pending:
            segment = draft.get("metadata", {}).get("segment", "unknown")
            by_segment[segment] = by_segment.get(segment, 0) + 1
        
        return {
            "total_pending": len(pending),
            "by_segment": by_segment,
            "drafts": pending[:100]  # Limit response size
        }
        
    except Exception as e:
        logger.error(f"Failed to get campaign queue: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get campaign queue: {str(e)}"
        )
