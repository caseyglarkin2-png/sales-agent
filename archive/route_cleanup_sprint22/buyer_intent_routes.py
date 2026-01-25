"""
Buyer Intent Routes - Intent signal tracking and analysis
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

router = APIRouter(prefix="/buyer-intent", tags=["Buyer Intent"])


class IntentSource(str, Enum):
    WEBSITE = "website"
    EMAIL = "email"
    ADVERTISING = "advertising"
    SOCIAL = "social"
    THIRD_PARTY = "third_party"
    CONTENT = "content"
    REVIEW_SITES = "review_sites"
    SEARCH = "search"
    EVENTS = "events"


class IntentStrength(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class BuyingStage(str, Enum):
    UNAWARE = "unaware"
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    PURCHASE = "purchase"


class IntentTopic(str, Enum):
    PRODUCT_RESEARCH = "product_research"
    PRICING = "pricing"
    COMPETITOR_COMPARISON = "competitor_comparison"
    REVIEWS = "reviews"
    IMPLEMENTATION = "implementation"
    INTEGRATION = "integration"
    USE_CASE = "use_case"
    DEMO_REQUEST = "demo_request"
    TRIAL = "trial"


class IntentSignalCreate(BaseModel):
    account_id: Optional[str] = None
    contact_id: Optional[str] = None
    source: IntentSource
    topic: Optional[IntentTopic] = None
    strength: IntentStrength
    description: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class IntentRuleCreate(BaseModel):
    name: str
    source: IntentSource
    topic: Optional[IntentTopic] = None
    conditions: List[Dict[str, Any]]
    strength_weight: int = Field(ge=1, le=100, default=50)
    notify_on_trigger: bool = False


# In-memory storage
intent_signals = {}
intent_rules = {}
intent_topics = {}
account_intent_scores = {}
intent_alerts = {}
topic_research = {}
surge_alerts = {}


# Intent Signals
@router.post("/signals")
async def record_intent_signal(
    request: IntentSignalCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Record an intent signal"""
    signal_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    signal = {
        "id": signal_id,
        "account_id": request.account_id,
        "contact_id": request.contact_id,
        "source": request.source.value,
        "topic": request.topic.value if request.topic else None,
        "strength": request.strength.value,
        "strength_score": get_strength_score(request.strength),
        "description": request.description,
        "url": request.url,
        "metadata": request.metadata or {},
        "tenant_id": tenant_id,
        "recorded_at": now.isoformat(),
        "recorded_by": user_id
    }
    
    intent_signals[signal_id] = signal
    
    # Update account intent score if applicable
    if request.account_id:
        update_account_intent_score(request.account_id, signal, tenant_id)
    
    # Check for surge
    check_intent_surge(request.account_id, tenant_id)
    
    logger.info("intent_signal_recorded", signal_id=signal_id, source=request.source.value)
    return signal


@router.get("/signals")
async def list_intent_signals(
    account_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    source: Optional[IntentSource] = None,
    topic: Optional[IntentTopic] = None,
    strength: Optional[IntentStrength] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List intent signals"""
    result = [s for s in intent_signals.values() if s.get("tenant_id") == tenant_id]
    
    if account_id:
        result = [s for s in result if s.get("account_id") == account_id]
    if contact_id:
        result = [s for s in result if s.get("contact_id") == contact_id]
    if source:
        result = [s for s in result if s.get("source") == source.value]
    if topic:
        result = [s for s in result if s.get("topic") == topic.value]
    if strength:
        result = [s for s in result if s.get("strength") == strength.value]
    if start_date:
        result = [s for s in result if s.get("recorded_at", "") >= start_date]
    if end_date:
        result = [s for s in result if s.get("recorded_at", "") <= end_date]
    
    result.sort(key=lambda x: x.get("recorded_at", ""), reverse=True)
    
    return {
        "signals": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/signals/{signal_id}")
async def get_intent_signal(signal_id: str):
    """Get signal details"""
    if signal_id not in intent_signals:
        raise HTTPException(status_code=404, detail="Signal not found")
    return intent_signals[signal_id]


# Account Intent Scores
@router.get("/accounts/{account_id}/intent-score")
async def get_account_intent_score(account_id: str, tenant_id: str = Query(default="default")):
    """Get intent score for an account"""
    if account_id not in account_intent_scores:
        return calculate_account_intent(account_id, tenant_id)
    return account_intent_scores[account_id]


@router.get("/accounts/{account_id}/intent-timeline")
async def get_account_intent_timeline(
    account_id: str,
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get intent timeline for an account"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    signals = [
        s for s in intent_signals.values()
        if s.get("tenant_id") == tenant_id
        and s.get("account_id") == account_id
        and s.get("recorded_at", "") >= cutoff
    ]
    
    signals.sort(key=lambda x: x.get("recorded_at", ""))
    
    # Group by day
    daily_intent = {}
    for signal in signals:
        date = signal.get("recorded_at", "")[:10]
        if date not in daily_intent:
            daily_intent[date] = {"count": 0, "total_score": 0, "signals": []}
        daily_intent[date]["count"] += 1
        daily_intent[date]["total_score"] += signal.get("strength_score", 0)
        daily_intent[date]["signals"].append(signal)
    
    timeline = [
        {"date": date, "signal_count": data["count"], "intent_score": data["total_score"]}
        for date, data in sorted(daily_intent.items())
    ]
    
    return {
        "account_id": account_id,
        "period_days": days,
        "timeline": timeline,
        "total_signals": len(signals),
        "avg_daily_score": sum(t["intent_score"] for t in timeline) / len(timeline) if timeline else 0
    }


@router.get("/accounts/top-intent")
async def get_top_intent_accounts(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get accounts with highest intent signals"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    # Aggregate by account
    account_scores = {}
    for signal in intent_signals.values():
        if signal.get("tenant_id") != tenant_id:
            continue
        if signal.get("recorded_at", "") < cutoff:
            continue
        
        account_id = signal.get("account_id")
        if not account_id:
            continue
        
        if account_id not in account_scores:
            account_scores[account_id] = {
                "account_id": account_id,
                "signal_count": 0,
                "total_score": 0,
                "topics": set(),
                "sources": set()
            }
        
        account_scores[account_id]["signal_count"] += 1
        account_scores[account_id]["total_score"] += signal.get("strength_score", 0)
        if signal.get("topic"):
            account_scores[account_id]["topics"].add(signal["topic"])
        account_scores[account_id]["sources"].add(signal.get("source"))
    
    # Convert sets to lists
    for account in account_scores.values():
        account["topics"] = list(account["topics"])
        account["sources"] = list(account["sources"])
    
    # Sort by total score
    ranked = sorted(account_scores.values(), key=lambda x: x["total_score"], reverse=True)
    
    return {
        "period_days": days,
        "accounts": ranked[:limit],
        "total_accounts_with_intent": len(ranked)
    }


# Intent Rules
@router.post("/rules")
async def create_intent_rule(
    request: IntentRuleCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create an intent tracking rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "source": request.source.value,
        "topic": request.topic.value if request.topic else None,
        "conditions": request.conditions,
        "strength_weight": request.strength_weight,
        "notify_on_trigger": request.notify_on_trigger,
        "is_active": True,
        "trigger_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    intent_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_intent_rules(
    source: Optional[IntentSource] = None,
    is_active: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List intent rules"""
    result = [r for r in intent_rules.values() if r.get("tenant_id") == tenant_id]
    
    if source:
        result = [r for r in result if r.get("source") == source.value]
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    
    return {"rules": result, "total": len(result)}


@router.put("/rules/{rule_id}")
async def update_intent_rule(
    rule_id: str,
    is_active: Optional[bool] = None,
    strength_weight: Optional[int] = None,
    notify_on_trigger: Optional[bool] = None
):
    """Update intent rule"""
    if rule_id not in intent_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = intent_rules[rule_id]
    
    if is_active is not None:
        rule["is_active"] = is_active
    if strength_weight is not None:
        rule["strength_weight"] = strength_weight
    if notify_on_trigger is not None:
        rule["notify_on_trigger"] = notify_on_trigger
    
    rule["updated_at"] = datetime.utcnow().isoformat()
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_intent_rule(rule_id: str):
    """Delete intent rule"""
    if rule_id not in intent_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    del intent_rules[rule_id]
    
    return {"status": "deleted", "rule_id": rule_id}


# Topic Tracking
@router.get("/topics/trending")
async def get_trending_topics(
    days: int = Query(default=7, ge=1, le=30),
    tenant_id: str = Query(default="default")
):
    """Get trending intent topics"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    topic_counts = {}
    for signal in intent_signals.values():
        if signal.get("tenant_id") != tenant_id:
            continue
        if signal.get("recorded_at", "") < cutoff:
            continue
        
        topic = signal.get("topic")
        if topic:
            if topic not in topic_counts:
                topic_counts[topic] = {"count": 0, "total_strength": 0}
            topic_counts[topic]["count"] += 1
            topic_counts[topic]["total_strength"] += signal.get("strength_score", 0)
    
    trending = [
        {
            "topic": topic,
            "signal_count": data["count"],
            "avg_strength": round(data["total_strength"] / data["count"], 1),
            "trend": random.choice(["up", "stable", "down"])
        }
        for topic, data in sorted(topic_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    ]
    
    return {
        "period_days": days,
        "trending_topics": trending,
        "total_signals": sum(t["signal_count"] for t in trending)
    }


@router.get("/topics/{topic}/accounts")
async def get_accounts_researching_topic(
    topic: IntentTopic,
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Get accounts researching a specific topic"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    account_data = {}
    for signal in intent_signals.values():
        if signal.get("tenant_id") != tenant_id:
            continue
        if signal.get("topic") != topic.value:
            continue
        if signal.get("recorded_at", "") < cutoff:
            continue
        
        account_id = signal.get("account_id")
        if not account_id:
            continue
        
        if account_id not in account_data:
            account_data[account_id] = {"signal_count": 0, "total_strength": 0, "latest_signal": ""}
        
        account_data[account_id]["signal_count"] += 1
        account_data[account_id]["total_strength"] += signal.get("strength_score", 0)
        if signal.get("recorded_at", "") > account_data[account_id]["latest_signal"]:
            account_data[account_id]["latest_signal"] = signal["recorded_at"]
    
    accounts = [
        {"account_id": aid, **data}
        for aid, data in sorted(account_data.items(), key=lambda x: x[1]["total_strength"], reverse=True)
    ]
    
    return {
        "topic": topic.value,
        "period_days": days,
        "accounts": accounts[:limit],
        "total_accounts": len(accounts)
    }


# Buying Stage Detection
@router.get("/accounts/{account_id}/buying-stage")
async def detect_buying_stage(account_id: str, tenant_id: str = Query(default="default")):
    """Detect buying stage based on intent signals"""
    signals = [
        s for s in intent_signals.values()
        if s.get("tenant_id") == tenant_id and s.get("account_id") == account_id
    ]
    
    if not signals:
        return {
            "account_id": account_id,
            "buying_stage": BuyingStage.UNAWARE.value,
            "confidence": 0.0,
            "signals_analyzed": 0
        }
    
    # Analyze topics to determine stage
    topic_counts = {}
    for signal in signals:
        topic = signal.get("topic")
        if topic:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    stage = detect_stage_from_topics(topic_counts)
    
    return {
        "account_id": account_id,
        "buying_stage": stage["stage"],
        "confidence": stage["confidence"],
        "signals_analyzed": len(signals),
        "key_topics": list(topic_counts.keys())[:5],
        "stage_indicators": stage["indicators"]
    }


# Surge Alerts
@router.get("/surge-alerts")
async def get_surge_alerts(
    is_active: Optional[bool] = True,
    tenant_id: str = Query(default="default")
):
    """Get intent surge alerts"""
    result = [a for a in surge_alerts.values() if a.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [a for a in result if a.get("is_active") == is_active]
    
    result.sort(key=lambda x: x.get("detected_at", ""), reverse=True)
    
    return {"alerts": result, "total": len(result)}


@router.post("/surge-alerts/{alert_id}/acknowledge")
async def acknowledge_surge_alert(alert_id: str, user_id: str = Query(default="default")):
    """Acknowledge a surge alert"""
    if alert_id not in surge_alerts:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = surge_alerts[alert_id]
    alert["is_active"] = False
    alert["acknowledged_by"] = user_id
    alert["acknowledged_at"] = datetime.utcnow().isoformat()
    
    return alert


# Analytics
@router.get("/analytics/overview")
async def get_intent_overview(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get intent analytics overview"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    period_signals = [
        s for s in intent_signals.values()
        if s.get("tenant_id") == tenant_id and s.get("recorded_at", "") >= cutoff
    ]
    
    unique_accounts = set(s.get("account_id") for s in period_signals if s.get("account_id"))
    
    by_source = {}
    for source in IntentSource:
        by_source[source.value] = len([s for s in period_signals if s.get("source") == source.value])
    
    by_strength = {}
    for strength in IntentStrength:
        by_strength[strength.value] = len([s for s in period_signals if s.get("strength") == strength.value])
    
    return {
        "period_days": days,
        "total_signals": len(period_signals),
        "unique_accounts": len(unique_accounts),
        "avg_signals_per_account": round(len(period_signals) / max(1, len(unique_accounts)), 1),
        "by_source": by_source,
        "by_strength": by_strength,
        "high_intent_accounts": len([
            aid for aid in unique_accounts
            if sum(s.get("strength_score", 0) for s in period_signals if s.get("account_id") == aid) >= 100
        ]),
        "active_surge_alerts": len([a for a in surge_alerts.values() if a.get("tenant_id") == tenant_id and a.get("is_active")])
    }


@router.get("/analytics/source-effectiveness")
async def get_source_effectiveness(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Analyze effectiveness of intent sources"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    period_signals = [
        s for s in intent_signals.values()
        if s.get("tenant_id") == tenant_id and s.get("recorded_at", "") >= cutoff
    ]
    
    source_data = {}
    for signal in period_signals:
        source = signal.get("source")
        if source not in source_data:
            source_data[source] = {"count": 0, "total_strength": 0, "unique_accounts": set()}
        
        source_data[source]["count"] += 1
        source_data[source]["total_strength"] += signal.get("strength_score", 0)
        if signal.get("account_id"):
            source_data[source]["unique_accounts"].add(signal["account_id"])
    
    effectiveness = [
        {
            "source": source,
            "signal_count": data["count"],
            "unique_accounts": len(data["unique_accounts"]),
            "avg_strength": round(data["total_strength"] / data["count"], 1),
            "effectiveness_score": round((data["total_strength"] / max(1, data["count"])) * len(data["unique_accounts"]) / 10, 1)
        }
        for source, data in source_data.items()
    ]
    
    return {
        "period_days": days,
        "sources": sorted(effectiveness, key=lambda x: x["effectiveness_score"], reverse=True)
    }


# Helper functions
def get_strength_score(strength: IntentStrength) -> int:
    """Convert strength enum to numeric score"""
    scores = {
        IntentStrength.VERY_HIGH: 100,
        IntentStrength.HIGH: 75,
        IntentStrength.MEDIUM: 50,
        IntentStrength.LOW: 25,
        IntentStrength.VERY_LOW: 10
    }
    return scores.get(strength, 50)


def update_account_intent_score(account_id: str, signal: Dict, tenant_id: str):
    """Update the intent score for an account"""
    if account_id not in account_intent_scores:
        account_intent_scores[account_id] = {
            "account_id": account_id,
            "current_score": 0,
            "signal_count": 0,
            "last_updated": None
        }
    
    score_data = account_intent_scores[account_id]
    score_data["signal_count"] += 1
    # Weighted running average
    new_score = (score_data["current_score"] * 0.7) + (signal.get("strength_score", 50) * 0.3)
    score_data["current_score"] = round(new_score, 1)
    score_data["last_updated"] = datetime.utcnow().isoformat()


def calculate_account_intent(account_id: str, tenant_id: str) -> Dict[str, Any]:
    """Calculate intent score for an account"""
    signals = [
        s for s in intent_signals.values()
        if s.get("account_id") == account_id
    ]
    
    if not signals:
        return {"account_id": account_id, "current_score": 0, "signal_count": 0}
    
    total_score = sum(s.get("strength_score", 0) for s in signals)
    
    return {
        "account_id": account_id,
        "current_score": min(100, total_score / len(signals)),
        "signal_count": len(signals),
        "last_signal_at": max(s.get("recorded_at", "") for s in signals)
    }


def check_intent_surge(account_id: Optional[str], tenant_id: str):
    """Check for intent surge and create alert if detected"""
    if not account_id:
        return
    
    # Check recent signals
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    recent = [
        s for s in intent_signals.values()
        if s.get("account_id") == account_id and s.get("recorded_at", "") >= cutoff
    ]
    
    # Surge detection: 5+ signals in 24 hours or very high strength
    if len(recent) >= 5 or any(s.get("strength") == "very_high" for s in recent):
        alert_id = str(uuid.uuid4())
        surge_alerts[alert_id] = {
            "id": alert_id,
            "account_id": account_id,
            "tenant_id": tenant_id,
            "signal_count": len(recent),
            "total_strength": sum(s.get("strength_score", 0) for s in recent),
            "is_active": True,
            "detected_at": datetime.utcnow().isoformat()
        }


def detect_stage_from_topics(topic_counts: Dict[str, int]) -> Dict[str, Any]:
    """Detect buying stage from topic signals"""
    total = sum(topic_counts.values())
    
    # Decision indicators
    decision_topics = {"demo_request", "trial", "pricing"}
    decision_signals = sum(topic_counts.get(t, 0) for t in decision_topics)
    
    # Consideration indicators
    consideration_topics = {"competitor_comparison", "reviews", "implementation"}
    consideration_signals = sum(topic_counts.get(t, 0) for t in consideration_topics)
    
    # Awareness indicators
    awareness_topics = {"product_research", "use_case", "integration"}
    awareness_signals = sum(topic_counts.get(t, 0) for t in awareness_topics)
    
    if decision_signals >= total * 0.4:
        return {
            "stage": BuyingStage.DECISION.value,
            "confidence": min(0.95, 0.6 + decision_signals / total * 0.4),
            "indicators": list(decision_topics.intersection(topic_counts.keys()))
        }
    elif consideration_signals >= total * 0.3:
        return {
            "stage": BuyingStage.CONSIDERATION.value,
            "confidence": min(0.85, 0.5 + consideration_signals / total * 0.4),
            "indicators": list(consideration_topics.intersection(topic_counts.keys()))
        }
    elif awareness_signals > 0:
        return {
            "stage": BuyingStage.AWARENESS.value,
            "confidence": min(0.75, 0.4 + awareness_signals / total * 0.4),
            "indicators": list(awareness_topics.intersection(topic_counts.keys()))
        }
    
    return {
        "stage": BuyingStage.UNAWARE.value,
        "confidence": 0.5,
        "indicators": []
    }
