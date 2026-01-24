"""Outcome tracking API endpoints.

Endpoints for:
- Recording outcomes (reply, meeting, deal change)
- Querying outcomes for queue items and contacts
- Getting outcome statistics for learning
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.outcomes import OutcomeType, OutcomeSource, OutcomeRecord, get_impact_score
from src.outcomes.service import get_outcome_service
from src.outcomes.detector import get_outcome_detector
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/outcomes", tags=["outcomes"])


class RecordOutcomeRequest(BaseModel):
    """Request to record an outcome."""
    outcome_type: OutcomeType
    source: OutcomeSource
    queue_item_id: Optional[str] = None
    action_id: Optional[str] = None
    signal_id: Optional[str] = None
    contact_email: Optional[str] = None
    deal_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class OutcomeResponse(BaseModel):
    """Response with outcome details."""
    id: str
    outcome_type: str
    source: str
    queue_item_id: Optional[str]
    action_id: Optional[str]
    contact_email: Optional[str]
    deal_id: Optional[str]
    context: Dict[str, Any]
    confidence: float
    impact_score: float
    detected_at: str


class OutcomeStatsResponse(BaseModel):
    """Response with outcome statistics."""
    period_days: int
    total_outcomes: int
    by_type: Dict[str, int]
    positive_outcomes: int
    negative_outcomes: int
    net_impact: float
    avg_impact: float
    reply_rate: float
    meeting_rate: float


class GmailReplyRequest(BaseModel):
    """Request to record a Gmail reply detection."""
    thread_id: str
    from_email: str
    to_email: str
    subject: str
    received_at: Optional[datetime] = None
    queue_item_id: Optional[str] = None
    action_id: Optional[str] = None


class DealChangeRequest(BaseModel):
    """Request to record a HubSpot deal change."""
    deal_id: str
    old_stage: str
    new_stage: str
    deal_name: str
    contact_email: Optional[str] = None
    queue_item_id: Optional[str] = None


class MeetingOutcomeRequest(BaseModel):
    """Request to record a meeting outcome."""
    meeting_id: str
    contact_email: str
    scheduled_time: datetime
    actual_outcome: str  # "held", "no_show", "rescheduled"
    queue_item_id: Optional[str] = None


def _to_response(outcome: OutcomeRecord) -> OutcomeResponse:
    """Convert OutcomeRecord to API response."""
    return OutcomeResponse(
        id=outcome.id,
        outcome_type=outcome.outcome_type.value,
        source=outcome.source.value,
        queue_item_id=outcome.queue_item_id,
        action_id=outcome.action_id,
        contact_email=outcome.contact_email,
        deal_id=outcome.deal_id,
        context=outcome.context,
        confidence=outcome.confidence,
        impact_score=outcome.impact_score,
        detected_at=outcome.detected_at.isoformat()
    )


@router.post("/record", response_model=OutcomeResponse)
async def record_outcome(request: RecordOutcomeRequest):
    """Record a new outcome.
    
    Use this to manually record outcomes or from webhooks.
    Outcomes feed into APS learning to improve recommendations.
    """
    service = get_outcome_service()
    
    outcome = await service.record_outcome(
        outcome_type=request.outcome_type,
        source=request.source,
        queue_item_id=request.queue_item_id,
        action_id=request.action_id,
        signal_id=request.signal_id,
        contact_email=request.contact_email,
        deal_id=request.deal_id,
        context=request.context,
        confidence=request.confidence
    )
    
    return _to_response(outcome)


# NOTE: Static routes MUST be defined before parameterized routes
# to avoid /{outcome_id} matching "types", "recent", "stats", etc.

@router.get("/types")
async def list_outcome_types():
    """List all outcome types with their default impact scores."""
    return {
        "outcome_types": [
            {
                "type": ot.value,
                "impact_score": get_impact_score(ot),
                "category": _categorize_outcome(ot)
            }
            for ot in OutcomeType
        ]
    }


@router.get("/recent", response_model=List[OutcomeResponse])
async def get_recent_outcomes(
    limit: int = Query(50, le=200),
    outcome_type: Optional[OutcomeType] = None,
    source: Optional[OutcomeSource] = None
):
    """Get recent outcomes with optional filtering."""
    service = get_outcome_service()
    outcomes = await service.get_recent_outcomes(
        limit=limit,
        outcome_type=outcome_type,
        source=source
    )
    return [_to_response(o) for o in outcomes]


@router.get("/stats", response_model=OutcomeStatsResponse)
async def get_outcome_stats(
    days: int = Query(7, ge=1, le=90),
    contact_email: Optional[str] = None
):
    """Get outcome statistics for a time period.
    
    Returns aggregated metrics useful for understanding
    engagement rates and what's working.
    """
    service = get_outcome_service()
    stats = await service.get_outcome_stats(days=days, contact_email=contact_email)
    return OutcomeStatsResponse(**stats)


@router.get("/queue/{queue_item_id}", response_model=List[OutcomeResponse])
async def get_outcomes_for_queue_item(queue_item_id: str):
    """Get all outcomes for a specific queue item."""
    service = get_outcome_service()
    outcomes = await service.get_outcomes_for_queue_item(queue_item_id)
    return [_to_response(o) for o in outcomes]


@router.get("/contact/{contact_email}", response_model=List[OutcomeResponse])
async def get_outcomes_for_contact(contact_email: str):
    """Get all outcomes for a specific contact."""
    service = get_outcome_service()
    outcomes = await service.get_outcomes_for_contact(contact_email)
    return [_to_response(o) for o in outcomes]


@router.get("/contact/{contact_email}/score-adjustment")
async def get_contact_score_adjustment(contact_email: str):
    """Get APS score adjustment for a contact based on outcome history.
    
    Returns a modifier (-20 to +20) that should be applied to
    APS scoring for actions involving this contact.
    """
    service = get_outcome_service()
    adjustment = await service.calculate_contact_score_adjustment(contact_email)
    
    return {
        "contact_email": contact_email,
        "score_adjustment": adjustment,
        "interpretation": _interpret_adjustment(adjustment)
    }


# Parameterized route LAST to avoid matching static paths
@router.get("/{outcome_id}", response_model=OutcomeResponse)
async def get_outcome(outcome_id: str):
    """Get a specific outcome by ID."""
    service = get_outcome_service()
    outcome = await service.get_outcome(outcome_id)
    
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    
    return _to_response(outcome)


@router.post("/detect/gmail-reply", response_model=OutcomeResponse)
async def detect_gmail_reply(request: GmailReplyRequest):
    """Record a detected Gmail reply.
    
    Call this when polling detects a reply in a thread we initiated.
    """
    detector = get_outcome_detector()
    
    outcome = await detector.detect_gmail_reply(
        thread_id=request.thread_id,
        from_email=request.from_email,
        to_email=request.to_email,
        subject=request.subject,
        received_at=request.received_at or datetime.utcnow(),
        queue_item_id=request.queue_item_id,
        action_id=request.action_id
    )
    
    return _to_response(outcome)


@router.post("/detect/deal-change", response_model=OutcomeResponse)
async def detect_deal_change(request: DealChangeRequest):
    """Record a detected HubSpot deal stage change.
    
    Call this when polling detects a deal moved stages.
    """
    detector = get_outcome_detector()
    
    outcome = await detector.detect_hubspot_deal_change(
        deal_id=request.deal_id,
        old_stage=request.old_stage,
        new_stage=request.new_stage,
        deal_name=request.deal_name,
        contact_email=request.contact_email,
        queue_item_id=request.queue_item_id
    )
    
    return _to_response(outcome)


@router.post("/detect/meeting", response_model=OutcomeResponse)
async def detect_meeting_outcome(request: MeetingOutcomeRequest):
    """Record a meeting outcome.
    
    Call this after a scheduled meeting to record if it was held,
    no-show, or rescheduled.
    """
    detector = get_outcome_detector()
    
    outcome = await detector.detect_meeting_outcome(
        meeting_id=request.meeting_id,
        contact_email=request.contact_email,
        scheduled_time=request.scheduled_time,
        actual_outcome=request.actual_outcome,
        queue_item_id=request.queue_item_id
    )
    
    return _to_response(outcome)


def _interpret_adjustment(adjustment: float) -> str:
    """Interpret a score adjustment for display."""
    if adjustment >= 10:
        return "Highly engaged - prioritize this contact"
    elif adjustment >= 5:
        return "Positive history - good candidate"
    elif adjustment >= 0:
        return "Neutral history"
    elif adjustment >= -5:
        return "Some negative signals"
    else:
        return "Poor engagement history - deprioritize"


def _categorize_outcome(outcome_type: OutcomeType) -> str:
    """Categorize outcome type."""
    if "email" in outcome_type.value.lower():
        return "email"
    elif "meeting" in outcome_type.value.lower():
        return "meeting"
    elif "deal" in outcome_type.value.lower():
        return "deal"
    elif "task" in outcome_type.value.lower():
        return "task"
    else:
        return "general"
