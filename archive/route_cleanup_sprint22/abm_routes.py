"""
Account-Based Marketing (ABM) Routes - Target account orchestration
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

router = APIRouter(prefix="/abm", tags=["Account-Based Marketing"])


class AccountTier(str, Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class AccountStatus(str, Enum):
    TARGET = "target"
    ENGAGED = "engaged"
    OPPORTUNITY = "opportunity"
    CUSTOMER = "customer"
    CHURNED = "churned"


class PlayType(str, Enum):
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"
    PIPELINE = "pipeline"
    EXPANSION = "expansion"
    RETENTION = "retention"


class ChannelType(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    ADVERTISING = "advertising"
    DIRECT_MAIL = "direct_mail"
    EVENTS = "events"
    CONTENT = "content"
    CALLING = "calling"
    GIFTING = "gifting"


class TargetAccountCreate(BaseModel):
    account_id: str
    company_name: str
    tier: AccountTier
    industry: Optional[str] = None
    employees: Optional[int] = None
    revenue: Optional[float] = None
    website: Optional[str] = None
    owner_id: Optional[str] = None
    target_contacts: Optional[List[str]] = None
    notes: Optional[str] = None


class PlayCreate(BaseModel):
    name: str
    play_type: PlayType
    description: Optional[str] = None
    target_tiers: List[AccountTier]
    channels: List[ChannelType]
    steps: List[Dict[str, Any]]
    success_metrics: Optional[Dict[str, Any]] = None
    budget_per_account: Optional[float] = None


class TouchCreate(BaseModel):
    account_id: str
    channel: ChannelType
    touch_type: str
    description: str
    contact_id: Optional[str] = None
    outcome: Optional[str] = None


# In-memory storage
target_accounts = {}
abm_plays = {}
account_touches = {}
buying_committees = {}
intent_signals = {}
account_journeys = {}
abm_campaigns = {}


# Target Accounts
@router.post("/accounts")
async def add_target_account(
    request: TargetAccountCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Add an account to ABM program"""
    now = datetime.utcnow()
    
    account = {
        "id": request.account_id,
        "company_name": request.company_name,
        "tier": request.tier.value,
        "status": AccountStatus.TARGET.value,
        "industry": request.industry,
        "employees": request.employees,
        "revenue": request.revenue,
        "website": request.website,
        "owner_id": request.owner_id,
        "target_contacts": request.target_contacts or [],
        "notes": request.notes,
        "engagement_score": 0,
        "intent_score": 0,
        "fit_score": calculate_fit_score(request),
        "touch_count": 0,
        "last_touch_date": None,
        "active_plays": [],
        "tenant_id": tenant_id,
        "added_at": now.isoformat(),
        "added_by": user_id
    }
    
    target_accounts[request.account_id] = account
    
    logger.info("target_account_added", account_id=request.account_id, tier=request.tier.value)
    return account


@router.get("/accounts")
async def list_target_accounts(
    tier: Optional[AccountTier] = None,
    status: Optional[AccountStatus] = None,
    owner_id: Optional[str] = None,
    min_engagement: Optional[int] = None,
    sort_by: str = Query(default="engagement_score", regex="^(engagement_score|fit_score|intent_score|company_name)$"),
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List target accounts"""
    result = [a for a in target_accounts.values() if a.get("tenant_id") == tenant_id]
    
    if tier:
        result = [a for a in result if a.get("tier") == tier.value]
    if status:
        result = [a for a in result if a.get("status") == status.value]
    if owner_id:
        result = [a for a in result if a.get("owner_id") == owner_id]
    if min_engagement is not None:
        result = [a for a in result if a.get("engagement_score", 0) >= min_engagement]
    
    # Sort
    reverse = sort_by != "company_name"
    result.sort(key=lambda x: x.get(sort_by, 0) if sort_by != "company_name" else x.get("company_name", ""), reverse=reverse)
    
    return {
        "accounts": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/accounts/{account_id}")
async def get_target_account(account_id: str):
    """Get target account details"""
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = target_accounts[account_id]
    touches = account_touches.get(account_id, [])
    committee = buying_committees.get(account_id, {})
    
    return {
        **account,
        "touches": touches[-20:],
        "buying_committee": committee,
        "total_touches": len(touches)
    }


@router.put("/accounts/{account_id}")
async def update_target_account(
    account_id: str,
    tier: Optional[AccountTier] = None,
    status: Optional[AccountStatus] = None,
    owner_id: Optional[str] = None,
    notes: Optional[str] = None
):
    """Update target account"""
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = target_accounts[account_id]
    
    if tier is not None:
        account["tier"] = tier.value
    if status is not None:
        account["status"] = status.value
    if owner_id is not None:
        account["owner_id"] = owner_id
    if notes is not None:
        account["notes"] = notes
    
    account["updated_at"] = datetime.utcnow().isoformat()
    
    return account


@router.delete("/accounts/{account_id}")
async def remove_target_account(account_id: str):
    """Remove account from ABM program"""
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    del target_accounts[account_id]
    
    return {"status": "removed", "account_id": account_id}


# Buying Committees
@router.post("/accounts/{account_id}/buying-committee")
async def set_buying_committee(
    account_id: str,
    members: List[Dict[str, Any]]
):
    """Define buying committee for an account"""
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    committee = {
        "account_id": account_id,
        "members": [
            {
                "contact_id": m.get("contact_id"),
                "name": m.get("name"),
                "title": m.get("title"),
                "role": m.get("role"),  # decision_maker, influencer, champion, blocker, user
                "engagement_status": m.get("engagement_status", "unknown"),
                "sentiment": m.get("sentiment", "neutral"),
                "is_engaged": False,
                "last_contact": None
            }
            for m in members
        ],
        "coverage_score": 0,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Calculate coverage
    roles_engaged = set(m["role"] for m in committee["members"] if m.get("is_engaged"))
    required_roles = {"decision_maker", "champion"}
    committee["coverage_score"] = len(roles_engaged.intersection(required_roles)) / len(required_roles) * 100
    
    buying_committees[account_id] = committee
    
    # Update account
    account = target_accounts[account_id]
    account["target_contacts"] = [m.get("contact_id") for m in members]
    
    return committee


@router.get("/accounts/{account_id}/buying-committee")
async def get_buying_committee(account_id: str):
    """Get buying committee"""
    if account_id not in buying_committees:
        return {"account_id": account_id, "members": [], "coverage_score": 0}
    return buying_committees[account_id]


@router.put("/accounts/{account_id}/buying-committee/{contact_id}")
async def update_committee_member(
    account_id: str,
    contact_id: str,
    engagement_status: Optional[str] = None,
    sentiment: Optional[str] = None,
    is_engaged: Optional[bool] = None
):
    """Update buying committee member"""
    if account_id not in buying_committees:
        raise HTTPException(status_code=404, detail="Buying committee not found")
    
    committee = buying_committees[account_id]
    
    for member in committee["members"]:
        if member.get("contact_id") == contact_id:
            if engagement_status is not None:
                member["engagement_status"] = engagement_status
            if sentiment is not None:
                member["sentiment"] = sentiment
            if is_engaged is not None:
                member["is_engaged"] = is_engaged
                member["last_contact"] = datetime.utcnow().isoformat()
            break
    
    committee["updated_at"] = datetime.utcnow().isoformat()
    
    return committee


# Touches
@router.post("/touches")
async def record_touch(
    request: TouchCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Record an ABM touch"""
    if request.account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    touch_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    touch = {
        "id": touch_id,
        "account_id": request.account_id,
        "channel": request.channel.value,
        "touch_type": request.touch_type,
        "description": request.description,
        "contact_id": request.contact_id,
        "outcome": request.outcome,
        "performed_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    if request.account_id not in account_touches:
        account_touches[request.account_id] = []
    account_touches[request.account_id].append(touch)
    
    # Update account
    account = target_accounts[request.account_id]
    account["touch_count"] = account.get("touch_count", 0) + 1
    account["last_touch_date"] = now.isoformat()
    
    # Update engagement score
    account["engagement_score"] = min(100, account.get("engagement_score", 0) + get_touch_points(request.channel, request.outcome))
    
    logger.info("touch_recorded", touch_id=touch_id, account_id=request.account_id, channel=request.channel.value)
    return touch


@router.get("/accounts/{account_id}/touches")
async def get_account_touches(
    account_id: str,
    channel: Optional[ChannelType] = None,
    limit: int = Query(default=50, le=100)
):
    """Get touches for an account"""
    touches = account_touches.get(account_id, [])
    
    if channel:
        touches = [t for t in touches if t.get("channel") == channel.value]
    
    touches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "touches": touches[:limit],
        "total": len(touches)
    }


# Plays
@router.post("/plays")
async def create_play(
    request: PlayCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create an ABM play"""
    play_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    play = {
        "id": play_id,
        "name": request.name,
        "play_type": request.play_type.value,
        "description": request.description,
        "target_tiers": [t.value for t in request.target_tiers],
        "channels": [c.value for c in request.channels],
        "steps": request.steps,
        "success_metrics": request.success_metrics or {},
        "budget_per_account": request.budget_per_account,
        "is_active": True,
        "accounts_enrolled": 0,
        "accounts_completed": 0,
        "success_rate": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    abm_plays[play_id] = play
    
    logger.info("abm_play_created", play_id=play_id, name=request.name)
    return play


@router.get("/plays")
async def list_plays(
    play_type: Optional[PlayType] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List ABM plays"""
    result = [p for p in abm_plays.values() if p.get("tenant_id") == tenant_id]
    
    if play_type:
        result = [p for p in result if p.get("play_type") == play_type.value]
    if is_active is not None:
        result = [p for p in result if p.get("is_active") == is_active]
    
    return {"plays": result, "total": len(result)}


@router.get("/plays/{play_id}")
async def get_play(play_id: str):
    """Get play details"""
    if play_id not in abm_plays:
        raise HTTPException(status_code=404, detail="Play not found")
    return abm_plays[play_id]


@router.post("/plays/{play_id}/enroll/{account_id}")
async def enroll_account_in_play(play_id: str, account_id: str):
    """Enroll account in a play"""
    if play_id not in abm_plays:
        raise HTTPException(status_code=404, detail="Play not found")
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    play = abm_plays[play_id]
    account = target_accounts[account_id]
    
    enrollment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    enrollment = {
        "id": enrollment_id,
        "play_id": play_id,
        "account_id": account_id,
        "status": "active",
        "current_step": 0,
        "steps_completed": [],
        "started_at": now.isoformat()
    }
    
    if account_id not in account_journeys:
        account_journeys[account_id] = []
    account_journeys[account_id].append(enrollment)
    
    # Update account and play
    account["active_plays"].append(play_id)
    play["accounts_enrolled"] = play.get("accounts_enrolled", 0) + 1
    
    return enrollment


# Intent Signals
@router.post("/accounts/{account_id}/intent")
async def record_intent_signal(
    account_id: str,
    signal_type: str,
    source: str,
    strength: int = Query(ge=1, le=100),
    details: Optional[Dict[str, Any]] = None
):
    """Record intent signal for account"""
    if account_id not in target_accounts:
        raise HTTPException(status_code=404, detail="Account not found")
    
    signal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    signal = {
        "id": signal_id,
        "account_id": account_id,
        "signal_type": signal_type,
        "source": source,
        "strength": strength,
        "details": details or {},
        "recorded_at": now.isoformat()
    }
    
    if account_id not in intent_signals:
        intent_signals[account_id] = []
    intent_signals[account_id].append(signal)
    
    # Update account intent score
    account = target_accounts[account_id]
    recent_signals = intent_signals[account_id][-10:]  # Last 10 signals
    account["intent_score"] = min(100, sum(s.get("strength", 0) for s in recent_signals) / len(recent_signals))
    
    return signal


@router.get("/accounts/{account_id}/intent")
async def get_account_intent(account_id: str, days: int = Query(default=30, ge=7, le=90)):
    """Get intent signals for account"""
    signals = intent_signals.get(account_id, [])
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    recent = [s for s in signals if s.get("recorded_at", "") >= cutoff]
    
    return {
        "account_id": account_id,
        "signals": recent,
        "total": len(recent),
        "avg_strength": sum(s.get("strength", 0) for s in recent) / len(recent) if recent else 0
    }


# Analytics
@router.get("/analytics/overview")
async def get_abm_overview(tenant_id: str = Query(default="default")):
    """Get ABM program overview"""
    tenant_accounts = [a for a in target_accounts.values() if a.get("tenant_id") == tenant_id]
    
    return {
        "total_accounts": len(tenant_accounts),
        "by_tier": {
            AccountTier.TIER_1.value: len([a for a in tenant_accounts if a.get("tier") == AccountTier.TIER_1.value]),
            AccountTier.TIER_2.value: len([a for a in tenant_accounts if a.get("tier") == AccountTier.TIER_2.value]),
            AccountTier.TIER_3.value: len([a for a in tenant_accounts if a.get("tier") == AccountTier.TIER_3.value])
        },
        "by_status": {
            status.value: len([a for a in tenant_accounts if a.get("status") == status.value])
            for status in AccountStatus
        },
        "avg_engagement_score": round(sum(a.get("engagement_score", 0) for a in tenant_accounts) / len(tenant_accounts), 1) if tenant_accounts else 0,
        "avg_fit_score": round(sum(a.get("fit_score", 0) for a in tenant_accounts) / len(tenant_accounts), 1) if tenant_accounts else 0,
        "total_touches": sum(len(account_touches.get(a["id"], [])) for a in tenant_accounts),
        "active_plays": len([p for p in abm_plays.values() if p.get("tenant_id") == tenant_id and p.get("is_active")]),
        "pipeline_from_abm": 2450000,
        "deals_from_abm": 18
    }


@router.get("/analytics/engagement")
async def get_engagement_analytics(
    tier: Optional[AccountTier] = None,
    tenant_id: str = Query(default="default")
):
    """Get engagement analytics"""
    tenant_accounts = [a for a in target_accounts.values() if a.get("tenant_id") == tenant_id]
    
    if tier:
        tenant_accounts = [a for a in tenant_accounts if a.get("tier") == tier.value]
    
    # Group by engagement level
    high_engagement = [a for a in tenant_accounts if a.get("engagement_score", 0) >= 70]
    medium_engagement = [a for a in tenant_accounts if 40 <= a.get("engagement_score", 0) < 70]
    low_engagement = [a for a in tenant_accounts if a.get("engagement_score", 0) < 40]
    
    return {
        "engagement_distribution": {
            "high": len(high_engagement),
            "medium": len(medium_engagement),
            "low": len(low_engagement)
        },
        "by_channel": {
            channel.value: sum(
                len([t for t in account_touches.get(a["id"], []) if t.get("channel") == channel.value])
                for a in tenant_accounts
            )
            for channel in ChannelType
        },
        "top_engaged_accounts": sorted(tenant_accounts, key=lambda x: x.get("engagement_score", 0), reverse=True)[:10],
        "accounts_needing_attention": [a for a in tenant_accounts if not a.get("last_touch_date") or a["last_touch_date"] < (datetime.utcnow() - timedelta(days=14)).isoformat()]
    }


@router.get("/analytics/journey")
async def get_journey_analytics(tenant_id: str = Query(default="default")):
    """Get account journey analytics"""
    tenant_accounts = [a for a in target_accounts.values() if a.get("tenant_id") == tenant_id]
    
    return {
        "stage_progression": {
            "target_to_engaged": 0.45,
            "engaged_to_opportunity": 0.32,
            "opportunity_to_customer": 0.28
        },
        "avg_time_to_engage_days": 21,
        "avg_touches_to_engage": 8,
        "avg_touches_to_opportunity": 15,
        "play_effectiveness": [
            {"play_id": p["id"], "name": p["name"], "success_rate": random.uniform(0.2, 0.5)}
            for p in list(abm_plays.values())[:5]
        ]
    }


# Helper functions
def calculate_fit_score(account: TargetAccountCreate) -> int:
    score = 50
    
    # Employee count scoring
    if account.employees:
        if 100 <= account.employees <= 1000:
            score += 25
        elif 1000 < account.employees <= 5000:
            score += 20
        elif account.employees > 5000:
            score += 15
    
    # Revenue scoring
    if account.revenue:
        if account.revenue >= 10000000:
            score += 20
        elif account.revenue >= 1000000:
            score += 15
    
    # Tier boost
    if account.tier == AccountTier.TIER_1:
        score += 10
    elif account.tier == AccountTier.TIER_2:
        score += 5
    
    return min(100, max(0, score))


def get_touch_points(channel: ChannelType, outcome: Optional[str]) -> int:
    base_points = {
        ChannelType.EMAIL: 3,
        ChannelType.LINKEDIN: 5,
        ChannelType.ADVERTISING: 2,
        ChannelType.DIRECT_MAIL: 8,
        ChannelType.EVENTS: 15,
        ChannelType.CONTENT: 5,
        ChannelType.CALLING: 10,
        ChannelType.GIFTING: 12
    }
    
    points = base_points.get(channel, 5)
    
    if outcome == "positive":
        points *= 2
    elif outcome == "meeting_booked":
        points *= 3
    elif outcome == "negative":
        points = points // 2
    
    return points
