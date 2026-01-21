"""
Campaign Routes.

API endpoints for campaign management.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
