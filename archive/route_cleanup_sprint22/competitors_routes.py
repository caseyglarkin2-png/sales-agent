"""
Competitors Routes - Competitive Intelligence API
==================================================
REST API for competitor tracking and battle cards.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any

from src.competitors.competitor_service import (
    get_competitor_service,
    CompetitorStatus,
    ThreatLevel,
    MentionSource,
    MentionOutcome,
)

router = APIRouter(prefix="/competitors", tags=["competitors"])


class CreateCompetitorRequest(BaseModel):
    """Request to create a competitor."""
    name: str
    website: str
    description: str
    status: str = "active"
    threat_level: str = "medium"
    logo_url: Optional[str] = None
    headquarters: Optional[str] = None
    employee_count: Optional[str] = None
    products: list[str] = []
    pricing_model: Optional[str] = None
    target_market: str = ""
    value_proposition: str = ""
    key_features: list[str] = []
    tags: list[str] = []


class UpdateCompetitorRequest(BaseModel):
    """Request to update a competitor."""
    name: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    threat_level: Optional[str] = None
    logo_url: Optional[str] = None
    headquarters: Optional[str] = None
    employee_count: Optional[str] = None
    products: Optional[list[str]] = None
    pricing_model: Optional[str] = None
    target_market: Optional[str] = None
    value_proposition: Optional[str] = None
    key_features: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None


class AddStrengthWeaknessRequest(BaseModel):
    """Request to add strength or weakness."""
    category: str
    description: str
    impact_score: int = 5
    evidence: str = ""


class RecordMentionRequest(BaseModel):
    """Request to record a mention."""
    source: str
    context: str = ""
    source_id: Optional[str] = None
    deal_amount: Optional[float] = None
    mentioned_by: Optional[str] = None


class UpdateMentionOutcomeRequest(BaseModel):
    """Request to update mention outcome."""
    outcome: str
    reason: Optional[str] = None


class CreateBattleCardRequest(BaseModel):
    """Request to create a battle card."""
    title: str
    overview: str = ""
    positioning: str = ""
    target_market: str = ""
    discovery_questions: list[str] = []
    talking_points: list[str] = []
    traps: list[str] = []
    differentiators: list[str] = []


class UpdateBattleCardRequest(BaseModel):
    """Request to update a battle card."""
    title: Optional[str] = None
    overview: Optional[str] = None
    positioning: Optional[str] = None
    target_market: Optional[str] = None
    discovery_questions: Optional[list[str]] = None
    talking_points: Optional[list[str]] = None
    traps: Optional[list[str]] = None
    differentiators: Optional[list[str]] = None


class AddObjectionHandlerRequest(BaseModel):
    """Request to add an objection handler."""
    objection: str
    response: str


class AddDiscoveryQuestionRequest(BaseModel):
    """Request to add a discovery question."""
    question: str


class PublishBattleCardRequest(BaseModel):
    """Request to publish a battle card."""
    reviewer_id: str


def competitor_to_dict(competitor) -> dict:
    """Convert competitor to dictionary."""
    return {
        "id": competitor.id,
        "name": competitor.name,
        "website": competitor.website,
        "description": competitor.description,
        "status": competitor.status.value,
        "threat_level": competitor.threat_level.value,
        "logo_url": competitor.logo_url,
        "founded_year": competitor.founded_year,
        "headquarters": competitor.headquarters,
        "employee_count": competitor.employee_count,
        "funding": competitor.funding,
        "revenue_estimate": competitor.revenue_estimate,
        "products": competitor.products,
        "pricing_model": competitor.pricing_model,
        "price_range": competitor.price_range,
        "target_market": competitor.target_market,
        "value_proposition": competitor.value_proposition,
        "key_features": competitor.key_features,
        "strengths": [
            {
                "id": s.id,
                "category": s.category,
                "description": s.description,
                "impact_score": s.impact_score,
            }
            for s in competitor.strengths
        ],
        "weaknesses": [
            {
                "id": w.id,
                "category": w.category,
                "description": w.description,
                "impact_score": w.impact_score,
            }
            for w in competitor.weaknesses
        ],
        "total_encounters": competitor.total_encounters,
        "wins_against": competitor.wins_against,
        "losses_to": competitor.losses_to,
        "win_rate": competitor.win_rate,
        "tags": competitor.tags,
        "battle_card_count": len(competitor.battle_cards),
        "mention_count": len(competitor.mentions),
        "created_at": competitor.created_at.isoformat(),
        "updated_at": competitor.updated_at.isoformat(),
    }


def battle_card_to_dict(card) -> dict:
    """Convert battle card to dictionary."""
    return {
        "id": card.id,
        "competitor_id": card.competitor_id,
        "title": card.title,
        "overview": card.overview,
        "positioning": card.positioning,
        "target_market": card.target_market,
        "strengths": [
            {
                "id": s.id,
                "category": s.category,
                "description": s.description,
                "impact_score": s.impact_score,
            }
            for s in card.strengths
        ],
        "weaknesses": [
            {
                "id": w.id,
                "category": w.category,
                "description": w.description,
                "impact_score": w.impact_score,
            }
            for w in card.weaknesses
        ],
        "discovery_questions": card.discovery_questions,
        "objection_handlers": card.objection_handlers,
        "talking_points": card.talking_points,
        "traps": card.traps,
        "differentiators": card.differentiators,
        "feature_comparison": card.feature_comparison,
        "case_studies": card.case_studies,
        "collateral_links": card.collateral_links,
        "is_published": card.is_published,
        "last_reviewed": card.last_reviewed.isoformat() if card.last_reviewed else None,
        "reviewed_by": card.reviewed_by,
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat(),
    }


@router.post("")
async def create_competitor(request: CreateCompetitorRequest):
    """Create a new competitor."""
    service = get_competitor_service()
    
    competitor = await service.create_competitor(
        name=request.name,
        website=request.website,
        description=request.description,
        status=CompetitorStatus(request.status),
        threat_level=ThreatLevel(request.threat_level),
        logo_url=request.logo_url,
        headquarters=request.headquarters,
        employee_count=request.employee_count,
        products=request.products,
        pricing_model=request.pricing_model,
        target_market=request.target_market,
        value_proposition=request.value_proposition,
        key_features=request.key_features,
        tags=request.tags,
    )
    
    return {"competitor": competitor_to_dict(competitor)}


@router.get("")
async def list_competitors(
    status: Optional[str] = None,
    threat_level: Optional[str] = None,
    search: Optional[str] = None
):
    """List competitors with filters."""
    service = get_competitor_service()
    
    status_enum = CompetitorStatus(status) if status else None
    threat_enum = ThreatLevel(threat_level) if threat_level else None
    
    competitors = await service.list_competitors(
        status=status_enum,
        threat_level=threat_enum,
        search=search
    )
    
    return {
        "competitors": [competitor_to_dict(c) for c in competitors],
        "count": len(competitors)
    }


@router.get("/win-loss-analysis")
async def get_win_loss_analysis():
    """Get overall win/loss analysis."""
    service = get_competitor_service()
    
    analysis = await service.get_win_loss_analysis()
    
    return analysis


@router.get("/{competitor_id}")
async def get_competitor(competitor_id: str):
    """Get a competitor by ID."""
    service = get_competitor_service()
    
    competitor = await service.get_competitor(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {"competitor": competitor_to_dict(competitor)}


@router.put("/{competitor_id}")
async def update_competitor(competitor_id: str, request: UpdateCompetitorRequest):
    """Update a competitor."""
    service = get_competitor_service()
    
    updates = request.model_dump(exclude_none=True)
    if "status" in updates:
        updates["status"] = CompetitorStatus(updates["status"])
    if "threat_level" in updates:
        updates["threat_level"] = ThreatLevel(updates["threat_level"])
    
    competitor = await service.update_competitor(competitor_id, updates)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {"competitor": competitor_to_dict(competitor)}


@router.delete("/{competitor_id}")
async def delete_competitor(competitor_id: str):
    """Delete a competitor."""
    service = get_competitor_service()
    
    success = await service.delete_competitor(competitor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {"success": True}


@router.get("/{competitor_id}/stats")
async def get_competitor_stats(competitor_id: str):
    """Get competitor statistics."""
    service = get_competitor_service()
    
    stats = await service.get_competitor_stats(competitor_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return stats


# Strengths and weaknesses
@router.post("/{competitor_id}/strengths")
async def add_strength(competitor_id: str, request: AddStrengthWeaknessRequest):
    """Add a strength to a competitor."""
    service = get_competitor_service()
    
    strength = await service.add_strength(
        competitor_id=competitor_id,
        category=request.category,
        description=request.description,
        impact_score=request.impact_score,
        evidence=request.evidence,
    )
    
    if not strength:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor = await service.get_competitor(competitor_id)
    
    return {"competitor": competitor_to_dict(competitor)}


@router.post("/{competitor_id}/weaknesses")
async def add_weakness(competitor_id: str, request: AddStrengthWeaknessRequest):
    """Add a weakness to a competitor."""
    service = get_competitor_service()
    
    weakness = await service.add_weakness(
        competitor_id=competitor_id,
        category=request.category,
        description=request.description,
        impact_score=request.impact_score,
        evidence=request.evidence,
    )
    
    if not weakness:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor = await service.get_competitor(competitor_id)
    
    return {"competitor": competitor_to_dict(competitor)}


@router.delete("/{competitor_id}/strengths-weaknesses/{item_id}")
async def remove_strength_or_weakness(competitor_id: str, item_id: str):
    """Remove a strength or weakness."""
    service = get_competitor_service()
    
    success = await service.remove_strength_or_weakness(competitor_id, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {"success": True}


# Mentions
@router.post("/{competitor_id}/mentions")
async def record_mention(competitor_id: str, request: RecordMentionRequest):
    """Record a competitor mention."""
    service = get_competitor_service()
    
    mention = await service.record_mention(
        competitor_id=competitor_id,
        source=MentionSource(request.source),
        context=request.context,
        source_id=request.source_id,
        deal_amount=request.deal_amount,
        mentioned_by=request.mentioned_by,
    )
    
    if not mention:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {
        "mention": {
            "id": mention.id,
            "competitor_id": mention.competitor_id,
            "source": mention.source.value,
            "context": mention.context,
            "outcome": mention.outcome.value,
            "mentioned_at": mention.mentioned_at.isoformat(),
        }
    }


@router.get("/{competitor_id}/mentions")
async def get_mentions(
    competitor_id: str,
    source: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get mentions for a competitor."""
    service = get_competitor_service()
    
    source_enum = MentionSource(source) if source else None
    outcome_enum = MentionOutcome(outcome) if outcome else None
    
    mentions = await service.get_mentions(
        competitor_id=competitor_id,
        source=source_enum,
        outcome=outcome_enum,
        limit=limit
    )
    
    return {
        "mentions": [
            {
                "id": m.id,
                "source": m.source.value,
                "source_id": m.source_id,
                "context": m.context,
                "deal_amount": m.deal_amount,
                "outcome": m.outcome.value,
                "won_reason": m.won_reason,
                "lost_reason": m.lost_reason,
                "mentioned_at": m.mentioned_at.isoformat(),
            }
            for m in mentions
        ],
        "count": len(mentions)
    }


@router.put("/mentions/{mention_id}/outcome")
async def update_mention_outcome(mention_id: str, request: UpdateMentionOutcomeRequest):
    """Update the outcome of a mention."""
    service = get_competitor_service()
    
    mention = await service.update_mention_outcome(
        mention_id=mention_id,
        outcome=MentionOutcome(request.outcome),
        reason=request.reason
    )
    
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    
    return {
        "mention": {
            "id": mention.id,
            "outcome": mention.outcome.value,
            "won_reason": mention.won_reason,
            "lost_reason": mention.lost_reason,
        }
    }


@router.get("/{competitor_id}/top-reasons")
async def get_top_reasons(
    competitor_id: str,
    outcome: str = Query(...),
    limit: int = Query(default=5, le=20)
):
    """Get top win/loss reasons against a competitor."""
    service = get_competitor_service()
    
    reasons = await service.get_top_reasons(
        competitor_id=competitor_id,
        outcome=MentionOutcome(outcome),
        limit=limit
    )
    
    return {"reasons": reasons}


# Battle cards
@router.post("/{competitor_id}/battle-cards")
async def create_battle_card(competitor_id: str, request: CreateBattleCardRequest):
    """Create a battle card."""
    service = get_competitor_service()
    
    card = await service.create_battle_card(
        competitor_id=competitor_id,
        title=request.title,
        overview=request.overview,
        positioning=request.positioning,
        target_market=request.target_market,
        discovery_questions=request.discovery_questions,
        talking_points=request.talking_points,
        traps=request.traps,
        differentiators=request.differentiators,
    )
    
    if not card:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    return {"battle_card": battle_card_to_dict(card)}


@router.get("/battle-cards")
async def list_battle_cards(
    competitor_id: Optional[str] = None,
    published_only: bool = False
):
    """List battle cards."""
    service = get_competitor_service()
    
    cards = await service.list_battle_cards(
        competitor_id=competitor_id,
        published_only=published_only
    )
    
    return {
        "battle_cards": [battle_card_to_dict(c) for c in cards],
        "count": len(cards)
    }


@router.get("/battle-cards/{battle_card_id}")
async def get_battle_card(battle_card_id: str):
    """Get a battle card by ID."""
    service = get_competitor_service()
    
    card = await service.get_battle_card(battle_card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    return {"battle_card": battle_card_to_dict(card)}


@router.put("/battle-cards/{battle_card_id}")
async def update_battle_card(battle_card_id: str, request: UpdateBattleCardRequest):
    """Update a battle card."""
    service = get_competitor_service()
    
    updates = request.model_dump(exclude_none=True)
    card = await service.update_battle_card(battle_card_id, updates)
    
    if not card:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    return {"battle_card": battle_card_to_dict(card)}


@router.post("/battle-cards/{battle_card_id}/publish")
async def publish_battle_card(battle_card_id: str, request: PublishBattleCardRequest):
    """Publish a battle card."""
    service = get_competitor_service()
    
    success = await service.publish_battle_card(battle_card_id, request.reviewer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    card = await service.get_battle_card(battle_card_id)
    
    return {"battle_card": battle_card_to_dict(card)}


@router.post("/battle-cards/{battle_card_id}/objection-handlers")
async def add_objection_handler(battle_card_id: str, request: AddObjectionHandlerRequest):
    """Add an objection handler."""
    service = get_competitor_service()
    
    success = await service.add_objection_handler(
        battle_card_id=battle_card_id,
        objection=request.objection,
        response=request.response
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    card = await service.get_battle_card(battle_card_id)
    
    return {"battle_card": battle_card_to_dict(card)}


@router.post("/battle-cards/{battle_card_id}/discovery-questions")
async def add_discovery_question(battle_card_id: str, request: AddDiscoveryQuestionRequest):
    """Add a discovery question."""
    service = get_competitor_service()
    
    success = await service.add_discovery_question(
        battle_card_id=battle_card_id,
        question=request.question
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Battle card not found")
    
    card = await service.get_battle_card(battle_card_id)
    
    return {"battle_card": battle_card_to_dict(card)}
