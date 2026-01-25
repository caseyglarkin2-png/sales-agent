"""
Revenue Attribution Routes - Multi-touch attribution and revenue tracking
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

router = APIRouter(prefix="/revenue-attribution", tags=["Revenue Attribution"])


class AttributionModel(str, Enum):
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    U_SHAPED = "u_shaped"
    W_SHAPED = "w_shaped"
    CUSTOM = "custom"


class TouchpointType(str, Enum):
    WEBSITE = "website"
    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    DEMO = "demo"
    WEBINAR = "webinar"
    CONTENT = "content"
    SOCIAL = "social"
    PAID_AD = "paid_ad"
    REFERRAL = "referral"
    EVENT = "event"
    DIRECT = "direct"


class Channel(str, Enum):
    ORGANIC_SEARCH = "organic_search"
    PAID_SEARCH = "paid_search"
    SOCIAL_ORGANIC = "social_organic"
    SOCIAL_PAID = "social_paid"
    EMAIL = "email"
    REFERRAL = "referral"
    DIRECT = "direct"
    DISPLAY = "display"
    AFFILIATE = "affiliate"
    EVENTS = "events"
    PARTNER = "partner"
    OUTBOUND = "outbound"


# In-memory storage
touchpoints = {}
journeys = {}
attribution_rules = {}
campaigns_attr = {}


class TouchpointCreate(BaseModel):
    touchpoint_type: TouchpointType
    channel: Channel
    source: Optional[str] = None
    campaign: Optional[str] = None
    content: Optional[str] = None
    deal_id: Optional[str] = None
    contact_id: str
    account_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AttributionRuleCreate(BaseModel):
    name: str
    model: AttributionModel
    weights: Optional[Dict[str, float]] = None
    time_decay_half_life_days: Optional[int] = None


# Touchpoints
@router.post("/touchpoints")
async def create_touchpoint(
    request: TouchpointCreate,
    tenant_id: str = Query(default="default")
):
    """Record a touchpoint"""
    touchpoint_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    touchpoint = {
        "id": touchpoint_id,
        "touchpoint_type": request.touchpoint_type.value,
        "channel": request.channel.value,
        "source": request.source,
        "campaign": request.campaign,
        "content": request.content,
        "deal_id": request.deal_id,
        "contact_id": request.contact_id,
        "account_id": request.account_id,
        "metadata": request.metadata or {},
        "tenant_id": tenant_id,
        "timestamp": now.isoformat()
    }
    
    touchpoints[touchpoint_id] = touchpoint
    
    return touchpoint


@router.get("/touchpoints")
async def list_touchpoints(
    contact_id: Optional[str] = None,
    account_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    channel: Optional[Channel] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    tenant_id: str = Query(default="default")
):
    """List touchpoints"""
    result = [t for t in touchpoints.values() if t.get("tenant_id") == tenant_id]
    
    if contact_id:
        result = [t for t in result if t.get("contact_id") == contact_id]
    if account_id:
        result = [t for t in result if t.get("account_id") == account_id]
    if deal_id:
        result = [t for t in result if t.get("deal_id") == deal_id]
    if channel:
        result = [t for t in result if t.get("channel") == channel.value]
    
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {"touchpoints": result[:limit], "total": len(result)}


# Attribution Analysis
@router.get("/deals/{deal_id}/attribution")
async def get_deal_attribution(
    deal_id: str,
    model: AttributionModel = Query(default=AttributionModel.LINEAR)
):
    """Get attribution for a specific deal"""
    # Simulate attribution data
    touchpoints_list = [
        {"type": "organic_search", "channel": "organic_search", "date": (datetime.utcnow() - timedelta(days=45)).isoformat()},
        {"type": "content", "channel": "organic_search", "date": (datetime.utcnow() - timedelta(days=40)).isoformat()},
        {"type": "email", "channel": "email", "date": (datetime.utcnow() - timedelta(days=30)).isoformat()},
        {"type": "webinar", "channel": "events", "date": (datetime.utcnow() - timedelta(days=20)).isoformat()},
        {"type": "demo", "channel": "direct", "date": (datetime.utcnow() - timedelta(days=10)).isoformat()},
        {"type": "meeting", "channel": "direct", "date": (datetime.utcnow() - timedelta(days=3)).isoformat()}
    ]
    
    deal_value = random.randint(10000, 100000)
    
    # Calculate attribution based on model
    attributed = []
    if model == AttributionModel.FIRST_TOUCH:
        for i, tp in enumerate(touchpoints_list):
            attributed.append({
                **tp,
                "credit": 1.0 if i == 0 else 0.0,
                "revenue": deal_value if i == 0 else 0
            })
    elif model == AttributionModel.LAST_TOUCH:
        for i, tp in enumerate(touchpoints_list):
            attributed.append({
                **tp,
                "credit": 1.0 if i == len(touchpoints_list) - 1 else 0.0,
                "revenue": deal_value if i == len(touchpoints_list) - 1 else 0
            })
    elif model == AttributionModel.LINEAR:
        credit = 1.0 / len(touchpoints_list)
        for tp in touchpoints_list:
            attributed.append({
                **tp,
                "credit": round(credit, 4),
                "revenue": round(deal_value * credit)
            })
    elif model == AttributionModel.U_SHAPED:
        for i, tp in enumerate(touchpoints_list):
            if i == 0 or i == len(touchpoints_list) - 1:
                credit = 0.4
            else:
                credit = 0.2 / (len(touchpoints_list) - 2)
            attributed.append({
                **tp,
                "credit": round(credit, 4),
                "revenue": round(deal_value * credit)
            })
    else:
        # Time decay
        weights = [0.5 ** i for i in range(len(touchpoints_list) - 1, -1, -1)]
        total_weight = sum(weights)
        for i, tp in enumerate(touchpoints_list):
            credit = weights[i] / total_weight
            attributed.append({
                **tp,
                "credit": round(credit, 4),
                "revenue": round(deal_value * credit)
            })
    
    return {
        "deal_id": deal_id,
        "deal_value": deal_value,
        "model": model.value,
        "touchpoints": attributed,
        "journey_days": 45,
        "touchpoint_count": len(touchpoints_list)
    }


@router.get("/channels/attribution")
async def get_channel_attribution(
    model: AttributionModel = Query(default=AttributionModel.LINEAR),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get attribution by channel"""
    channels = [c.value for c in Channel]
    
    total_revenue = random.randint(500000, 2000000)
    channel_data = []
    
    weights = [random.uniform(0.05, 0.2) for _ in channels]
    total_weight = sum(weights)
    
    for i, channel in enumerate(channels):
        share = weights[i] / total_weight
        channel_data.append({
            "channel": channel,
            "attributed_revenue": round(total_revenue * share),
            "attribution_share": round(share, 4),
            "deals": random.randint(5, 50),
            "touchpoints": random.randint(50, 500),
            "avg_touches_before_conversion": round(random.uniform(2, 8), 1),
            "roi": round(random.uniform(1.5, 10), 2)
        })
    
    channel_data.sort(key=lambda x: x["attributed_revenue"], reverse=True)
    
    return {
        "model": model.value,
        "total_revenue": total_revenue,
        "channels": channel_data
    }


@router.get("/campaigns/attribution")
async def get_campaign_attribution(
    model: AttributionModel = Query(default=AttributionModel.LINEAR),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get attribution by campaign"""
    campaigns = [
        "Q4 Product Launch", "Summer Webinar Series", "Enterprise Outbound",
        "SMB Email Nurture", "Partner Co-Marketing", "LinkedIn Ads - Decision Makers",
        "Google Search - Brand", "Content Syndication", "Industry Event 2024"
    ]
    
    total_revenue = random.randint(500000, 2000000)
    campaign_data = []
    
    for campaign in campaigns:
        revenue = random.randint(20000, 200000)
        spend = random.randint(5000, 50000)
        
        campaign_data.append({
            "campaign": campaign,
            "attributed_revenue": revenue,
            "spend": spend,
            "roi": round(revenue / spend, 2),
            "roas": round(revenue / spend, 2),
            "deals": random.randint(2, 30),
            "pipeline_influenced": random.randint(50000, 500000),
            "first_touch_conversions": random.randint(1, 20),
            "last_touch_conversions": random.randint(1, 15),
            "assisted_conversions": random.randint(5, 50)
        })
    
    campaign_data.sort(key=lambda x: x["attributed_revenue"], reverse=True)
    
    return {
        "model": model.value,
        "campaigns": campaign_data[:limit],
        "total_attributed": sum(c["attributed_revenue"] for c in campaign_data),
        "total_spend": sum(c["spend"] for c in campaign_data)
    }


# Customer Journey
@router.get("/contacts/{contact_id}/journey")
async def get_contact_journey(contact_id: str):
    """Get contact's full attribution journey"""
    touchpoints_count = random.randint(5, 20)
    journey = []
    
    touchpoint_types = list(TouchpointType)
    channels = list(Channel)
    
    for i in range(touchpoints_count):
        days_ago = touchpoints_count * 5 - (i * 5) + random.randint(-2, 2)
        
        journey.append({
            "order": i + 1,
            "timestamp": (datetime.utcnow() - timedelta(days=days_ago)).isoformat(),
            "touchpoint_type": random.choice(touchpoint_types).value,
            "channel": random.choice(channels).value,
            "source": random.choice(["google", "linkedin", "direct", "email_campaign", "partner"]),
            "content": f"Content piece {random.randint(1, 100)}",
            "engagement_score": random.randint(1, 10)
        })
    
    return {
        "contact_id": contact_id,
        "journey": journey,
        "summary": {
            "first_touch": journey[0]["timestamp"] if journey else None,
            "last_touch": journey[-1]["timestamp"] if journey else None,
            "total_touchpoints": len(journey),
            "journey_days": touchpoints_count * 5,
            "channels_used": len(set(j["channel"] for j in journey)),
            "primary_channel": max(set(j["channel"] for j in journey), key=lambda x: sum(1 for j in journey if j["channel"] == x)) if journey else None
        }
    }


@router.get("/accounts/{account_id}/journey")
async def get_account_journey(account_id: str):
    """Get account's attribution journey (all contacts)"""
    contacts_count = random.randint(2, 8)
    contact_journeys = []
    
    for i in range(contacts_count):
        contact_id = f"contact_{i+1}"
        touchpoints_count = random.randint(3, 10)
        
        contact_journeys.append({
            "contact_id": contact_id,
            "role": random.choice(["Decision Maker", "Champion", "Influencer", "End User"]),
            "touchpoints": touchpoints_count,
            "first_touch": (datetime.utcnow() - timedelta(days=random.randint(30, 120))).isoformat()
        })
    
    return {
        "account_id": account_id,
        "contacts": contact_journeys,
        "summary": {
            "total_contacts": contacts_count,
            "total_touchpoints": sum(c["touchpoints"] for c in contact_journeys),
            "buying_committee_coverage": round(random.uniform(0.4, 0.9), 2),
            "engagement_score": random.randint(50, 100)
        }
    }


# Attribution Rules
@router.post("/rules")
async def create_attribution_rule(
    request: AttributionRuleCreate,
    tenant_id: str = Query(default="default")
):
    """Create custom attribution rule"""
    rule_id = str(uuid.uuid4())
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "model": request.model.value,
        "weights": request.weights or {},
        "time_decay_half_life_days": request.time_decay_half_life_days,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    attribution_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_attribution_rules(tenant_id: str = Query(default="default")):
    """List attribution rules"""
    result = [r for r in attribution_rules.values() if r.get("tenant_id") == tenant_id]
    
    # Add default models
    defaults = [
        {"id": "default_first", "name": "First Touch (Default)", "model": "first_touch", "is_default": True},
        {"id": "default_last", "name": "Last Touch (Default)", "model": "last_touch", "is_default": True},
        {"id": "default_linear", "name": "Linear (Default)", "model": "linear", "is_default": True},
        {"id": "default_time_decay", "name": "Time Decay (Default)", "model": "time_decay", "is_default": True},
        {"id": "default_u_shaped", "name": "U-Shaped (Default)", "model": "u_shaped", "is_default": True}
    ]
    
    return {"rules": defaults + result, "total": len(defaults) + len(result)}


# Model Comparison
@router.get("/compare-models")
async def compare_attribution_models(
    deal_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Compare attribution across different models"""
    channels = ["organic_search", "paid_search", "email", "social_paid", "direct", "referral"]
    total_revenue = random.randint(500000, 1500000)
    
    comparison = {}
    for model in AttributionModel:
        channel_attribution = {}
        weights = [random.uniform(0.1, 0.3) for _ in channels]
        total_weight = sum(weights)
        
        for i, channel in enumerate(channels):
            share = weights[i] / total_weight
            channel_attribution[channel] = {
                "revenue": round(total_revenue * share),
                "share": round(share, 4)
            }
        
        comparison[model.value] = channel_attribution
    
    return {
        "total_revenue": total_revenue,
        "models": comparison,
        "recommendation": "Linear or Time Decay models recommended for B2B sales cycles"
    }


# Reports
@router.get("/reports/roi")
async def get_roi_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    model: AttributionModel = Query(default=AttributionModel.LINEAR),
    tenant_id: str = Query(default="default")
):
    """Get ROI report by channel and campaign"""
    channels = list(Channel)
    
    roi_data = []
    for channel in channels:
        spend = random.randint(5000, 100000)
        revenue = round(spend * random.uniform(1.5, 8))
        
        roi_data.append({
            "channel": channel.value,
            "spend": spend,
            "attributed_revenue": revenue,
            "roi": round((revenue - spend) / spend, 2),
            "roas": round(revenue / spend, 2),
            "cac": round(spend / random.randint(5, 50)),
            "deals_won": random.randint(5, 50)
        })
    
    roi_data.sort(key=lambda x: x["roi"], reverse=True)
    
    return {
        "model": model.value,
        "channels": roi_data,
        "totals": {
            "spend": sum(c["spend"] for c in roi_data),
            "revenue": sum(c["attributed_revenue"] for c in roi_data),
            "overall_roi": round((sum(c["attributed_revenue"] for c in roi_data) - sum(c["spend"] for c in roi_data)) / sum(c["spend"] for c in roi_data), 2)
        }
    }


@router.get("/reports/pipeline-influence")
async def get_pipeline_influence_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get pipeline influence report"""
    channels = list(Channel)
    
    influence_data = []
    total_pipeline = random.randint(2000000, 10000000)
    
    for channel in channels:
        influenced = random.randint(100000, 1000000)
        
        influence_data.append({
            "channel": channel.value,
            "pipeline_influenced": influenced,
            "deals_touched": random.randint(20, 200),
            "avg_deal_size": round(influenced / random.randint(10, 50)),
            "conversion_rate": round(random.uniform(0.1, 0.4), 3)
        })
    
    influence_data.sort(key=lambda x: x["pipeline_influenced"], reverse=True)
    
    return {
        "total_pipeline": total_pipeline,
        "channels": influence_data
    }


# Dashboard
@router.get("/dashboard")
async def get_attribution_dashboard(
    model: AttributionModel = Query(default=AttributionModel.LINEAR),
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get attribution dashboard"""
    total_revenue = random.randint(500000, 2000000)
    
    return {
        "model": model.value,
        "period_days": days,
        "total_attributed_revenue": total_revenue,
        "top_channels": [
            {"channel": "organic_search", "revenue": int(total_revenue * 0.25)},
            {"channel": "email", "revenue": int(total_revenue * 0.20)},
            {"channel": "paid_search", "revenue": int(total_revenue * 0.18)},
            {"channel": "direct", "revenue": int(total_revenue * 0.15)},
            {"channel": "referral", "revenue": int(total_revenue * 0.12)}
        ],
        "top_campaigns": [
            {"campaign": "Q4 Launch", "revenue": random.randint(50000, 200000)},
            {"campaign": "Enterprise Outbound", "revenue": random.randint(40000, 150000)},
            {"campaign": "Webinar Series", "revenue": random.randint(30000, 100000)}
        ],
        "avg_touchpoints_to_close": round(random.uniform(5, 12), 1),
        "avg_journey_days": random.randint(30, 90),
        "multi_touch_vs_single": {
            "multi_touch_deals": random.randint(70, 90),
            "single_touch_deals": random.randint(10, 30)
        }
    }
