"""
Competitive Intelligence Routes - Track and analyze competitors
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/competitive-intelligence", tags=["Competitive Intelligence"])


class CompetitorTier(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EMERGING = "emerging"
    LEGACY = "legacy"


class ThreatLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class IntelType(str, Enum):
    PRICING = "pricing"
    FEATURE = "feature"
    POSITIONING = "positioning"
    CUSTOMER_WIN = "customer_win"
    CUSTOMER_LOSS = "customer_loss"
    FUNDING = "funding"
    HIRING = "hiring"
    PARTNERSHIP = "partnership"
    PRODUCT_LAUNCH = "product_launch"
    NEWS = "news"


class DealOutcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    ONGOING = "ongoing"


class CompetitorCreate(BaseModel):
    name: str
    website: Optional[str] = None
    tier: CompetitorTier = CompetitorTier.SECONDARY
    description: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    primary_industries: Optional[List[str]] = None
    pricing_model: Optional[str] = None
    target_company_size: Optional[List[str]] = None


class IntelCreate(BaseModel):
    competitor_id: str
    intel_type: IntelType
    title: str
    description: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    confidence: int = Field(ge=1, le=10, default=5)
    is_verified: bool = False


class CompetitiveWinLoss(BaseModel):
    competitor_id: str
    deal_id: str
    outcome: DealOutcome
    deal_size: Optional[float] = None
    reasons: Optional[List[str]] = None
    notes: Optional[str] = None


# In-memory storage
competitors = {}
intel_items = {}
win_loss_records = {}
battle_cards = {}
feature_comparisons = {}
pricing_intel = {}
alerts_config = {}
competitive_alerts = {}


# Competitors
@router.post("/competitors")
async def create_competitor(
    request: CompetitorCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a competitor profile"""
    competitor_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    competitor = {
        "id": competitor_id,
        "name": request.name,
        "website": request.website,
        "tier": request.tier.value,
        "threat_level": ThreatLevel.UNKNOWN.value,
        "description": request.description,
        "strengths": request.strengths or [],
        "weaknesses": request.weaknesses or [],
        "primary_industries": request.primary_industries or [],
        "pricing_model": request.pricing_model,
        "target_company_size": request.target_company_size or [],
        "win_rate_against": 0.0,
        "deals_encountered": 0,
        "intel_count": 0,
        "last_intel_date": None,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    competitors[competitor_id] = competitor
    
    logger.info("competitor_created", competitor_id=competitor_id, name=request.name)
    return competitor


@router.get("/competitors")
async def list_competitors(
    tier: Optional[CompetitorTier] = None,
    threat_level: Optional[ThreatLevel] = None,
    industry: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List competitors"""
    result = [c for c in competitors.values() if c.get("tenant_id") == tenant_id]
    
    if tier:
        result = [c for c in result if c.get("tier") == tier.value]
    if threat_level:
        result = [c for c in result if c.get("threat_level") == threat_level.value]
    if industry:
        result = [c for c in result if industry in c.get("primary_industries", [])]
    
    return {"competitors": result, "total": len(result)}


@router.get("/competitors/{competitor_id}")
async def get_competitor(competitor_id: str):
    """Get competitor details"""
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor = competitors[competitor_id]
    intel = [i for i in intel_items.values() if i.get("competitor_id") == competitor_id]
    wl = [r for r in win_loss_records.values() if r.get("competitor_id") == competitor_id]
    
    return {
        **competitor,
        "recent_intel": sorted(intel, key=lambda x: x.get("created_at", ""), reverse=True)[:10],
        "win_loss_summary": {
            "wins": len([r for r in wl if r.get("outcome") == "win"]),
            "losses": len([r for r in wl if r.get("outcome") == "loss"]),
            "ongoing": len([r for r in wl if r.get("outcome") == "ongoing"])
        }
    }


@router.put("/competitors/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    tier: Optional[CompetitorTier] = None,
    threat_level: Optional[ThreatLevel] = None,
    strengths: Optional[List[str]] = None,
    weaknesses: Optional[List[str]] = None,
    description: Optional[str] = None
):
    """Update competitor"""
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    competitor = competitors[competitor_id]
    
    if tier is not None:
        competitor["tier"] = tier.value
    if threat_level is not None:
        competitor["threat_level"] = threat_level.value
    if strengths is not None:
        competitor["strengths"] = strengths
    if weaknesses is not None:
        competitor["weaknesses"] = weaknesses
    if description is not None:
        competitor["description"] = description
    
    competitor["updated_at"] = datetime.utcnow().isoformat()
    
    return competitor


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(competitor_id: str):
    """Delete competitor"""
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    del competitors[competitor_id]
    
    return {"status": "deleted", "competitor_id": competitor_id}


# Intel
@router.post("/intel")
async def add_intel(
    request: IntelCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Add competitive intelligence"""
    if request.competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    intel_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    intel = {
        "id": intel_id,
        "competitor_id": request.competitor_id,
        "intel_type": request.intel_type.value,
        "title": request.title,
        "description": request.description,
        "source": request.source,
        "source_url": request.source_url,
        "confidence": request.confidence,
        "is_verified": request.is_verified,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    intel_items[intel_id] = intel
    
    # Update competitor
    competitor = competitors[request.competitor_id]
    competitor["intel_count"] = competitor.get("intel_count", 0) + 1
    competitor["last_intel_date"] = now.isoformat()
    
    logger.info("intel_added", intel_id=intel_id, competitor_id=request.competitor_id)
    return intel


@router.get("/intel")
async def list_intel(
    competitor_id: Optional[str] = None,
    intel_type: Optional[IntelType] = None,
    is_verified: Optional[bool] = None,
    start_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List intel items"""
    result = [i for i in intel_items.values() if i.get("tenant_id") == tenant_id]
    
    if competitor_id:
        result = [i for i in result if i.get("competitor_id") == competitor_id]
    if intel_type:
        result = [i for i in result if i.get("intel_type") == intel_type.value]
    if is_verified is not None:
        result = [i for i in result if i.get("is_verified") == is_verified]
    if start_date:
        result = [i for i in result if i.get("created_at", "") >= start_date]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "intel": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.put("/intel/{intel_id}/verify")
async def verify_intel(intel_id: str, user_id: str = Query(default="default")):
    """Mark intel as verified"""
    if intel_id not in intel_items:
        raise HTTPException(status_code=404, detail="Intel not found")
    
    intel = intel_items[intel_id]
    intel["is_verified"] = True
    intel["verified_by"] = user_id
    intel["verified_at"] = datetime.utcnow().isoformat()
    
    return intel


# Win/Loss Analysis
@router.post("/win-loss")
async def record_win_loss(
    request: CompetitiveWinLoss,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Record competitive win/loss"""
    if request.competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    record_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    record = {
        "id": record_id,
        "competitor_id": request.competitor_id,
        "deal_id": request.deal_id,
        "outcome": request.outcome.value,
        "deal_size": request.deal_size,
        "reasons": request.reasons or [],
        "notes": request.notes,
        "recorded_by": user_id,
        "tenant_id": tenant_id,
        "recorded_at": now.isoformat()
    }
    
    win_loss_records[record_id] = record
    
    # Update competitor stats
    update_competitor_win_rate(request.competitor_id)
    
    logger.info("win_loss_recorded", record_id=record_id, outcome=request.outcome.value)
    return record


@router.get("/win-loss")
async def get_win_loss_analysis(
    competitor_id: Optional[str] = None,
    outcome: Optional[DealOutcome] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get win/loss analysis"""
    result = [r for r in win_loss_records.values() if r.get("tenant_id") == tenant_id]
    
    if competitor_id:
        result = [r for r in result if r.get("competitor_id") == competitor_id]
    if outcome:
        result = [r for r in result if r.get("outcome") == outcome.value]
    if start_date:
        result = [r for r in result if r.get("recorded_at", "") >= start_date]
    if end_date:
        result = [r for r in result if r.get("recorded_at", "") <= end_date]
    
    wins = [r for r in result if r.get("outcome") == "win"]
    losses = [r for r in result if r.get("outcome") == "loss"]
    
    # Aggregate loss reasons
    loss_reasons = {}
    for r in losses:
        for reason in r.get("reasons", []):
            loss_reasons[reason] = loss_reasons.get(reason, 0) + 1
    
    win_reasons = {}
    for r in wins:
        for reason in r.get("reasons", []):
            win_reasons[reason] = win_reasons.get(reason, 0) + 1
    
    return {
        "summary": {
            "total_deals": len(result),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / max(1, len(wins) + len(losses)), 2),
            "total_won_value": sum(r.get("deal_size", 0) or 0 for r in wins),
            "total_lost_value": sum(r.get("deal_size", 0) or 0 for r in losses)
        },
        "top_loss_reasons": sorted(loss_reasons.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_win_reasons": sorted(win_reasons.items(), key=lambda x: x[1], reverse=True)[:10],
        "records": result
    }


# Battle Cards
@router.post("/competitors/{competitor_id}/battle-card")
async def create_battle_card(
    competitor_id: str,
    positioning: str,
    key_differentiators: List[str],
    objection_handlers: List[Dict[str, str]],
    trap_questions: Optional[List[str]] = None,
    landmines: Optional[List[str]] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create or update battle card for competitor"""
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    now = datetime.utcnow()
    
    battle_card = {
        "competitor_id": competitor_id,
        "competitor_name": competitors[competitor_id].get("name"),
        "positioning": positioning,
        "key_differentiators": key_differentiators,
        "objection_handlers": objection_handlers,
        "trap_questions": trap_questions or [],
        "landmines": landmines or [],
        "updated_by": user_id,
        "tenant_id": tenant_id,
        "updated_at": now.isoformat()
    }
    
    battle_cards[competitor_id] = battle_card
    
    return battle_card


@router.get("/competitors/{competitor_id}/battle-card")
async def get_battle_card(competitor_id: str):
    """Get battle card for competitor"""
    if competitor_id not in battle_cards:
        if competitor_id in competitors:
            return {"competitor_id": competitor_id, "message": "Battle card not created yet"}
        raise HTTPException(status_code=404, detail="Competitor not found")
    return battle_cards[competitor_id]


# Feature Comparison
@router.post("/feature-comparison")
async def update_feature_comparison(
    features: List[Dict[str, Any]],
    tenant_id: str = Query(default="default")
):
    """Update feature comparison matrix"""
    now = datetime.utcnow()
    
    comparison = {
        "features": features,  # [{"feature": "SSO", "us": true, "competitor_a": true, "competitor_b": false}]
        "updated_at": now.isoformat()
    }
    
    feature_comparisons[tenant_id] = comparison
    
    return comparison


@router.get("/feature-comparison")
async def get_feature_comparison(tenant_id: str = Query(default="default")):
    """Get feature comparison matrix"""
    if tenant_id not in feature_comparisons:
        return {"features": [], "message": "No comparison data yet"}
    return feature_comparisons[tenant_id]


# Pricing Intel
@router.post("/competitors/{competitor_id}/pricing")
async def update_pricing_intel(
    competitor_id: str,
    pricing_data: Dict[str, Any],
    source: Optional[str] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Update pricing intelligence for competitor"""
    if competitor_id not in competitors:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    now = datetime.utcnow()
    
    pricing = {
        "competitor_id": competitor_id,
        "pricing_data": pricing_data,
        "source": source,
        "updated_by": user_id,
        "tenant_id": tenant_id,
        "updated_at": now.isoformat()
    }
    
    pricing_intel[competitor_id] = pricing
    
    return pricing


@router.get("/competitors/{competitor_id}/pricing")
async def get_pricing_intel(competitor_id: str):
    """Get pricing intel for competitor"""
    if competitor_id not in pricing_intel:
        if competitor_id in competitors:
            return {"competitor_id": competitor_id, "message": "No pricing data yet"}
        raise HTTPException(status_code=404, detail="Competitor not found")
    return pricing_intel[competitor_id]


# Alerts
@router.post("/alerts/configure")
async def configure_alerts(
    competitor_ids: List[str],
    intel_types: List[IntelType],
    notify_email: Optional[str] = None,
    notify_slack: Optional[bool] = False,
    tenant_id: str = Query(default="default")
):
    """Configure competitive alerts"""
    config = {
        "competitor_ids": competitor_ids,
        "intel_types": [t.value for t in intel_types],
        "notify_email": notify_email,
        "notify_slack": notify_slack,
        "is_active": True,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    alerts_config[tenant_id] = config
    
    return config


@router.get("/alerts")
async def get_alerts(
    is_read: Optional[bool] = None,
    competitor_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get competitive alerts"""
    result = [a for a in competitive_alerts.values() if a.get("tenant_id") == tenant_id]
    
    if is_read is not None:
        result = [a for a in result if a.get("is_read") == is_read]
    if competitor_id:
        result = [a for a in result if a.get("competitor_id") == competitor_id]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"alerts": result[:limit], "total": len(result)}


# Analytics
@router.get("/analytics/overview")
async def get_competitive_overview(tenant_id: str = Query(default="default")):
    """Get competitive intelligence overview"""
    tenant_competitors = [c for c in competitors.values() if c.get("tenant_id") == tenant_id]
    tenant_intel = [i for i in intel_items.values() if i.get("tenant_id") == tenant_id]
    tenant_wl = [r for r in win_loss_records.values() if r.get("tenant_id") == tenant_id]
    
    wins = len([r for r in tenant_wl if r.get("outcome") == "win"])
    losses = len([r for r in tenant_wl if r.get("outcome") == "loss"])
    
    return {
        "total_competitors": len(tenant_competitors),
        "by_tier": {
            tier.value: len([c for c in tenant_competitors if c.get("tier") == tier.value])
            for tier in CompetitorTier
        },
        "by_threat_level": {
            tl.value: len([c for c in tenant_competitors if c.get("threat_level") == tl.value])
            for tl in ThreatLevel
        },
        "total_intel_items": len(tenant_intel),
        "intel_this_month": len([i for i in tenant_intel if i.get("created_at", "") >= (datetime.utcnow() - timedelta(days=30)).isoformat()]),
        "overall_win_rate": round(wins / max(1, wins + losses), 2),
        "deals_analyzed": len(tenant_wl),
        "battle_cards_created": len([b for b in battle_cards.values() if b.get("tenant_id") == tenant_id])
    }


@router.get("/analytics/competitor-ranking")
async def get_competitor_ranking(tenant_id: str = Query(default="default")):
    """Rank competitors by threat level and encounter frequency"""
    tenant_competitors = [c for c in competitors.values() if c.get("tenant_id") == tenant_id]
    
    # Calculate threat scores
    rankings = []
    for comp in tenant_competitors:
        wl = [r for r in win_loss_records.values() if r.get("competitor_id") == comp["id"]]
        wins = len([r for r in wl if r.get("outcome") == "win"])
        losses = len([r for r in wl if r.get("outcome") == "loss"])
        
        threat_score = 0
        if losses > 0:
            threat_score = (losses / max(1, wins + losses)) * 100
        
        # Factor in tier
        tier_multiplier = {"primary": 1.5, "secondary": 1.2, "emerging": 1.0, "legacy": 0.8}
        threat_score *= tier_multiplier.get(comp.get("tier"), 1.0)
        
        rankings.append({
            "competitor_id": comp["id"],
            "name": comp["name"],
            "tier": comp["tier"],
            "threat_score": round(threat_score, 1),
            "deals_encountered": wins + losses,
            "win_rate_against": round(wins / max(1, wins + losses), 2)
        })
    
    rankings.sort(key=lambda x: x["threat_score"], reverse=True)
    
    for i, r in enumerate(rankings):
        r["rank"] = i + 1
    
    return {"rankings": rankings}


# Helper functions
def update_competitor_win_rate(competitor_id: str):
    """Update win rate stats for competitor"""
    if competitor_id not in competitors:
        return
    
    wl = [r for r in win_loss_records.values() if r.get("competitor_id") == competitor_id]
    wins = len([r for r in wl if r.get("outcome") == "win"])
    losses = len([r for r in wl if r.get("outcome") == "loss"])
    
    competitor = competitors[competitor_id]
    competitor["deals_encountered"] = wins + losses
    competitor["win_rate_against"] = round(wins / max(1, wins + losses), 2)
    
    # Update threat level based on win rate
    if competitor["win_rate_against"] < 0.3:
        competitor["threat_level"] = ThreatLevel.HIGH.value
    elif competitor["win_rate_against"] < 0.5:
        competitor["threat_level"] = ThreatLevel.MEDIUM.value
    else:
        competitor["threat_level"] = ThreatLevel.LOW.value
