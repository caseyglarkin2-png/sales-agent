"""
Contact Scoring Routes.

API endpoints for contact scoring and prioritization.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.scoring import get_contact_scorer, ScoreTier, ICP_CRITERIA

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scoring", tags=["scoring"])


class ScoreContactRequest(BaseModel):
    email: str
    name: str
    company: str
    job_title: Optional[str] = None
    company_size: Optional[int] = None
    industry: Optional[str] = None
    engagements: Optional[List[Dict]] = None
    intent_signals: Optional[List[str]] = None


class BulkScoreRequest(BaseModel):
    contacts: List[ScoreContactRequest]


@router.get("/criteria")
async def get_criteria() -> Dict[str, Any]:
    """Get scoring criteria."""
    return {
        "criteria": ICP_CRITERIA,
        "weights": {
            "fit": 0.4,
            "engagement": 0.3,
            "intent": 0.3,
        },
        "tiers": [
            {"tier": "hot", "range": "80-100"},
            {"tier": "warm", "range": "60-79"},
            {"tier": "cool", "range": "40-59"},
            {"tier": "cold", "range": "0-39"},
        ],
    }


@router.post("/score")
async def score_contact(request: ScoreContactRequest) -> Dict[str, Any]:
    """Score a single contact."""
    scorer = get_contact_scorer()
    
    score = scorer.score_contact(
        email=request.email,
        name=request.name,
        company=request.company,
        job_title=request.job_title,
        company_size=request.company_size,
        industry=request.industry,
        engagements=request.engagements,
        intent_signals=request.intent_signals,
    )
    
    return {
        "status": "success",
        "score": score.to_dict(),
    }


@router.post("/score-bulk")
async def score_bulk(request: BulkScoreRequest) -> Dict[str, Any]:
    """Score multiple contacts."""
    scorer = get_contact_scorer()
    scored = []
    
    for contact in request.contacts:
        score = scorer.score_contact(
            email=contact.email,
            name=contact.name,
            company=contact.company,
            job_title=contact.job_title,
            company_size=contact.company_size,
            industry=contact.industry,
            engagements=contact.engagements,
            intent_signals=contact.intent_signals,
        )
        scored.append(score.to_dict())
    
    return {
        "status": "success",
        "scored": scored,
        "count": len(scored),
    }


@router.post("/score-hubspot/{email}")
async def score_from_hubspot(email: str) -> Dict[str, Any]:
    """Score a contact using HubSpot data."""
    scorer = get_contact_scorer()
    
    score = await scorer.score_from_hubspot(email)
    
    if not score:
        raise HTTPException(status_code=404, detail="Contact not found in HubSpot")
    
    return {
        "status": "success",
        "score": score.to_dict(),
    }


@router.get("/contact/{email}")
async def get_contact_score(email: str) -> Dict[str, Any]:
    """Get score for a specific contact."""
    scorer = get_contact_scorer()
    
    score = scorer.get_contact_score(email)
    
    if not score:
        raise HTTPException(status_code=404, detail="Contact not scored")
    
    return {
        "score": score,
    }


@router.get("/top")
async def get_top_contacts(
    tier: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get top scored contacts."""
    scorer = get_contact_scorer()
    
    tier_filter = None
    if tier:
        try:
            tier_filter = ScoreTier(tier)
        except ValueError:
            pass
    
    contacts = scorer.get_top_contacts(tier=tier_filter, limit=limit)
    
    return {
        "contacts": contacts,
        "count": len(contacts),
    }


@router.get("/distribution")
async def get_distribution() -> Dict[str, Any]:
    """Get score distribution by tier."""
    scorer = get_contact_scorer()
    
    return {
        "distribution": scorer.get_score_distribution(),
    }


@router.get("/hot")
async def get_hot_contacts(limit: int = 20) -> Dict[str, Any]:
    """Get hot-tier contacts."""
    scorer = get_contact_scorer()
    contacts = scorer.get_top_contacts(tier=ScoreTier.HOT, limit=limit)
    
    return {
        "contacts": contacts,
        "count": len(contacts),
    }
