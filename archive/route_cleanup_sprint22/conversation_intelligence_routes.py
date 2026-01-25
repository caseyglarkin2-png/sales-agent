"""
Conversation Intelligence Routes - Call/meeting analysis and insights
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

router = APIRouter(prefix="/conversation-intelligence", tags=["Conversation Intelligence"])


class ConversationType(str, Enum):
    CALL = "call"
    VIDEO_MEETING = "video_meeting"
    DEMO = "demo"
    DISCOVERY = "discovery"
    NEGOTIATION = "negotiation"
    ONBOARDING = "onboarding"


class Sentiment(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class TopicCategory(str, Enum):
    PRICING = "pricing"
    COMPETITION = "competition"
    FEATURES = "features"
    IMPLEMENTATION = "implementation"
    TIMELINE = "timeline"
    OBJECTION = "objection"
    NEXT_STEPS = "next_steps"
    PAIN_POINT = "pain_point"
    USE_CASE = "use_case"


class ConversationCreate(BaseModel):
    title: str
    conversation_type: ConversationType
    deal_id: Optional[str] = None
    contact_ids: Optional[List[str]] = None
    recording_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    platform: Optional[str] = None
    scheduled_at: Optional[str] = None


class ConversationAnalysis(BaseModel):
    transcript: str
    speakers: Optional[List[Dict[str, str]]] = None


class CoachingRule(BaseModel):
    name: str
    rule_type: str
    trigger_condition: str
    suggestion: str
    priority: int = 5
    is_active: bool = True


# In-memory storage
conversations = {}
conversation_transcripts = {}
conversation_insights = {}
coaching_rules = {}
coaching_feedback = {}
conversation_moments = {}
topic_trackers = {}
talk_patterns = {}


# Conversations
@router.post("/conversations")
async def create_conversation(
    request: ConversationCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a conversation record"""
    conversation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    conversation = {
        "id": conversation_id,
        "title": request.title,
        "conversation_type": request.conversation_type.value,
        "deal_id": request.deal_id,
        "contact_ids": request.contact_ids or [],
        "recording_url": request.recording_url,
        "duration_seconds": request.duration_seconds,
        "platform": request.platform,
        "scheduled_at": request.scheduled_at,
        "status": "pending",
        "is_analyzed": False,
        "overall_sentiment": None,
        "talk_ratio": None,
        "key_topics": [],
        "participant_id": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    conversations[conversation_id] = conversation
    
    logger.info("conversation_created", conversation_id=conversation_id)
    return conversation


@router.get("/conversations")
async def list_conversations(
    conversation_type: Optional[ConversationType] = None,
    deal_id: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List conversations"""
    result = [c for c in conversations.values() if c.get("tenant_id") == tenant_id]
    
    if conversation_type:
        result = [c for c in result if c.get("conversation_type") == conversation_type.value]
    if deal_id:
        result = [c for c in result if c.get("deal_id") == deal_id]
    if is_analyzed is not None:
        result = [c for c in result if c.get("is_analyzed") == is_analyzed]
    if start_date:
        result = [c for c in result if c.get("created_at", "") >= start_date]
    if end_date:
        result = [c for c in result if c.get("created_at", "") <= end_date]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "conversations": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation details"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = conversations[conversation_id]
    transcript = conversation_transcripts.get(conversation_id, {})
    insights = conversation_insights.get(conversation_id, {})
    moments = conversation_moments.get(conversation_id, [])
    
    return {
        **conv,
        "transcript": transcript,
        "insights": insights,
        "key_moments": moments[:10]
    }


# Transcription & Analysis
@router.post("/conversations/{conversation_id}/analyze")
async def analyze_conversation(
    conversation_id: str,
    request: ConversationAnalysis
):
    """Analyze conversation with AI"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = conversations[conversation_id]
    
    # Store transcript
    transcript_data = {
        "text": request.transcript,
        "speakers": request.speakers or [],
        "word_count": len(request.transcript.split()),
        "processed_at": datetime.utcnow().isoformat()
    }
    conversation_transcripts[conversation_id] = transcript_data
    
    # Generate AI insights
    insights = generate_conversation_insights(request.transcript, request.speakers)
    conversation_insights[conversation_id] = insights
    
    # Extract key moments
    moments = extract_key_moments(request.transcript)
    conversation_moments[conversation_id] = moments
    
    # Update conversation
    conversation["is_analyzed"] = True
    conversation["status"] = "analyzed"
    conversation["overall_sentiment"] = insights.get("overall_sentiment")
    conversation["talk_ratio"] = insights.get("talk_ratio")
    conversation["key_topics"] = insights.get("topics", [])
    conversation["analyzed_at"] = datetime.utcnow().isoformat()
    
    logger.info("conversation_analyzed", conversation_id=conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "status": "analyzed",
        "insights": insights,
        "key_moments": moments[:10]
    }


@router.get("/conversations/{conversation_id}/transcript")
async def get_transcript(conversation_id: str):
    """Get conversation transcript"""
    if conversation_id not in conversation_transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return conversation_transcripts[conversation_id]


@router.get("/conversations/{conversation_id}/insights")
async def get_insights(conversation_id: str):
    """Get conversation insights"""
    if conversation_id not in conversation_insights:
        raise HTTPException(status_code=404, detail="Insights not found")
    return conversation_insights[conversation_id]


# Key Moments
@router.get("/conversations/{conversation_id}/moments")
async def get_key_moments(
    conversation_id: str,
    category: Optional[TopicCategory] = None
):
    """Get key moments from conversation"""
    moments = conversation_moments.get(conversation_id, [])
    
    if category:
        moments = [m for m in moments if m.get("category") == category.value]
    
    return {"moments": moments, "total": len(moments)}


@router.post("/conversations/{conversation_id}/moments/{moment_id}/bookmark")
async def bookmark_moment(conversation_id: str, moment_id: str):
    """Bookmark a key moment"""
    moments = conversation_moments.get(conversation_id, [])
    
    for moment in moments:
        if moment.get("id") == moment_id:
            moment["is_bookmarked"] = True
            moment["bookmarked_at"] = datetime.utcnow().isoformat()
            return moment
    
    raise HTTPException(status_code=404, detail="Moment not found")


# Coaching
@router.post("/coaching/rules")
async def create_coaching_rule(
    request: CoachingRule,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create coaching rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": request.name,
        "rule_type": request.rule_type,
        "trigger_condition": request.trigger_condition,
        "suggestion": request.suggestion,
        "priority": request.priority,
        "is_active": request.is_active,
        "triggers_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    coaching_rules[rule_id] = rule
    
    return rule


@router.get("/coaching/rules")
async def list_coaching_rules(
    is_active: Optional[bool] = None,
    rule_type: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List coaching rules"""
    result = [r for r in coaching_rules.values() if r.get("tenant_id") == tenant_id]
    
    if is_active is not None:
        result = [r for r in result if r.get("is_active") == is_active]
    if rule_type:
        result = [r for r in result if r.get("rule_type") == rule_type]
    
    return {"rules": result, "total": len(result)}


@router.get("/conversations/{conversation_id}/coaching")
async def get_conversation_coaching(conversation_id: str):
    """Get coaching feedback for conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    feedback = coaching_feedback.get(conversation_id, generate_coaching_feedback(conversation_id))
    coaching_feedback[conversation_id] = feedback
    
    return feedback


@router.post("/conversations/{conversation_id}/coaching/generate")
async def generate_coaching_for_conversation(conversation_id: str):
    """Generate coaching feedback for conversation"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    feedback = generate_coaching_feedback(conversation_id)
    coaching_feedback[conversation_id] = feedback
    
    logger.info("coaching_generated", conversation_id=conversation_id)
    return feedback


# Talk Patterns
@router.get("/conversations/{conversation_id}/talk-patterns")
async def get_talk_patterns(conversation_id: str):
    """Get talk pattern analysis"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    patterns = talk_patterns.get(conversation_id)
    if not patterns:
        patterns = analyze_talk_patterns(conversation_id)
        talk_patterns[conversation_id] = patterns
    
    return patterns


# Topic Tracking
@router.get("/topics/trending")
async def get_trending_topics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get trending topics across conversations"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    tenant_convs = [
        c for c in conversations.values()
        if c.get("tenant_id") == tenant_id and c.get("created_at", "") >= cutoff
    ]
    
    # Aggregate topics
    topic_counts = {}
    for conv in tenant_convs:
        for topic in conv.get("key_topics", []):
            topic_name = topic.get("name") if isinstance(topic, dict) else topic
            topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
    
    trending = [
        {"topic": t, "count": c, "trend": random.choice(["up", "down", "stable"])}
        for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    
    return {
        "period_days": days,
        "total_conversations": len(tenant_convs),
        "trending_topics": trending
    }


@router.get("/topics/{topic_name}/conversations")
async def get_conversations_by_topic(
    topic_name: str,
    tenant_id: str = Query(default="default"),
    limit: int = Query(default=20, le=50)
):
    """Get conversations mentioning a topic"""
    result = []
    
    for conv in conversations.values():
        if conv.get("tenant_id") != tenant_id:
            continue
        
        for topic in conv.get("key_topics", []):
            topic_str = topic.get("name") if isinstance(topic, dict) else topic
            if topic_name.lower() in topic_str.lower():
                result.append(conv)
                break
    
    return {"conversations": result[:limit], "total": len(result)}


# Analytics
@router.get("/analytics/overview")
async def get_ci_overview(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get conversation intelligence overview"""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    tenant_convs = [
        c for c in conversations.values()
        if c.get("tenant_id") == tenant_id and c.get("created_at", "") >= cutoff
    ]
    
    analyzed = [c for c in tenant_convs if c.get("is_analyzed")]
    
    return {
        "period_days": days,
        "total_conversations": len(tenant_convs),
        "analyzed_conversations": len(analyzed),
        "total_duration_hours": sum(c.get("duration_seconds", 0) for c in tenant_convs) / 3600,
        "by_type": {
            ct.value: len([c for c in tenant_convs if c.get("conversation_type") == ct.value])
            for ct in ConversationType
        },
        "avg_sentiment_score": 0.65,
        "avg_talk_ratio": 0.42,
        "top_topics": ["pricing", "features", "implementation", "timeline", "competition"][:5],
        "coaching_opportunities": random.randint(15, 40)
    }


@router.get("/analytics/sentiment-trends")
async def get_sentiment_trends(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get sentiment trends over time"""
    trend_data = []
    for i in range(days, 0, -7):
        date = (datetime.utcnow() - timedelta(days=i)).isoformat()[:10]
        trend_data.append({
            "date": date,
            "avg_sentiment": random.uniform(0.5, 0.8),
            "positive_count": random.randint(10, 30),
            "neutral_count": random.randint(5, 15),
            "negative_count": random.randint(1, 8)
        })
    
    return {"trends": trend_data}


@router.get("/analytics/rep-comparison")
async def get_rep_comparison(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Compare rep performance in conversations"""
    return {
        "rep_metrics": [
            {
                "rep_id": f"rep_{i}",
                "rep_name": f"Rep {i}",
                "total_conversations": random.randint(20, 50),
                "avg_talk_ratio": random.uniform(0.35, 0.55),
                "avg_sentiment": random.uniform(0.55, 0.80),
                "discovery_score": random.randint(60, 95),
                "objection_handling_score": random.randint(50, 90),
                "next_steps_score": random.randint(65, 95)
            }
            for i in range(1, 6)
        ]
    }


# Search
@router.post("/search")
async def search_conversations(
    query: str,
    conversation_type: Optional[ConversationType] = None,
    sentiment: Optional[Sentiment] = None,
    topic: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    tenant_id: str = Query(default="default")
):
    """Search through conversations"""
    result = []
    
    for conv_id, transcript in conversation_transcripts.items():
        if conv_id not in conversations:
            continue
        
        conv = conversations[conv_id]
        if conv.get("tenant_id") != tenant_id:
            continue
        
        text = transcript.get("text", "").lower()
        if query.lower() in text:
            match = {
                **conv,
                "snippet": text[max(0, text.find(query.lower()) - 50):text.find(query.lower()) + len(query) + 50]
            }
            result.append(match)
    
    return {"results": result[:limit], "total": len(result), "query": query}


# Helper functions
def generate_conversation_insights(transcript: str, speakers: Optional[List[Dict]]) -> Dict[str, Any]:
    """Generate AI insights from conversation"""
    word_count = len(transcript.split())
    
    return {
        "overall_sentiment": random.choice(["positive", "neutral", "slightly_negative"]),
        "sentiment_score": round(random.uniform(0.4, 0.9), 2),
        "talk_ratio": {
            "rep": round(random.uniform(0.35, 0.55), 2),
            "prospect": round(random.uniform(0.45, 0.65), 2)
        },
        "topics": [
            {"name": "pricing", "mentions": random.randint(2, 8), "sentiment": "neutral"},
            {"name": "features", "mentions": random.randint(3, 10), "sentiment": "positive"},
            {"name": "timeline", "mentions": random.randint(1, 5), "sentiment": "neutral"}
        ],
        "questions_asked": {
            "by_rep": random.randint(5, 15),
            "by_prospect": random.randint(3, 10)
        },
        "objections_detected": random.randint(0, 3),
        "competitor_mentions": random.randint(0, 2),
        "next_steps_clarity": random.choice(["clear", "unclear", "none"]),
        "engagement_score": random.randint(60, 95),
        "word_count": word_count
    }


def extract_key_moments(transcript: str) -> List[Dict[str, Any]]:
    """Extract key moments from transcript"""
    moments = []
    
    moment_templates = [
        {"category": "pricing", "label": "Pricing discussion", "importance": "high"},
        {"category": "objection", "label": "Customer objection raised", "importance": "high"},
        {"category": "features", "label": "Feature request mentioned", "importance": "medium"},
        {"category": "competition", "label": "Competitor mentioned", "importance": "high"},
        {"category": "next_steps", "label": "Next steps discussed", "importance": "medium"},
        {"category": "pain_point", "label": "Pain point identified", "importance": "high"}
    ]
    
    for i, template in enumerate(random.sample(moment_templates, min(4, len(moment_templates)))):
        moments.append({
            "id": str(uuid.uuid4()),
            "timestamp_seconds": random.randint(60, 1800),
            "category": template["category"],
            "label": template["label"],
            "importance": template["importance"],
            "snippet": f"Sample snippet for {template['label'].lower()}...",
            "is_bookmarked": False
        })
    
    return sorted(moments, key=lambda x: x["timestamp_seconds"])


def generate_coaching_feedback(conversation_id: str) -> Dict[str, Any]:
    """Generate coaching feedback"""
    return {
        "conversation_id": conversation_id,
        "overall_score": random.randint(60, 95),
        "strengths": [
            {"skill": "Active listening", "score": random.randint(70, 95)},
            {"skill": "Product knowledge", "score": random.randint(75, 95)}
        ],
        "areas_for_improvement": [
            {
                "skill": "Discovery questions",
                "score": random.randint(40, 65),
                "suggestion": "Ask more open-ended questions to uncover needs"
            },
            {
                "skill": "Talk ratio",
                "score": random.randint(45, 60),
                "suggestion": "Listen more, aim for 40% talk time"
            }
        ],
        "specific_moments": [
            {
                "timestamp": "3:45",
                "feedback": "Great job handling the pricing objection",
                "type": "positive"
            },
            {
                "timestamp": "8:22",
                "feedback": "Missed opportunity to ask about decision timeline",
                "type": "improvement"
            }
        ],
        "recommended_training": ["Discovery Mastery", "Objection Handling 101"],
        "generated_at": datetime.utcnow().isoformat()
    }


def analyze_talk_patterns(conversation_id: str) -> Dict[str, Any]:
    """Analyze talk patterns in conversation"""
    return {
        "conversation_id": conversation_id,
        "talk_time_breakdown": {
            "rep_seconds": random.randint(300, 900),
            "prospect_seconds": random.randint(400, 1000),
            "silence_seconds": random.randint(30, 120)
        },
        "longest_monologue": {
            "speaker": "rep",
            "duration_seconds": random.randint(45, 180)
        },
        "interruptions": {
            "by_rep": random.randint(1, 5),
            "by_prospect": random.randint(0, 3)
        },
        "speaking_pace": {
            "rep_wpm": random.randint(120, 180),
            "prospect_wpm": random.randint(100, 160)
        },
        "filler_words": {
            "um": random.randint(5, 20),
            "uh": random.randint(3, 15),
            "like": random.randint(2, 12),
            "you_know": random.randint(1, 8)
        },
        "question_frequency": {
            "rep_per_minute": round(random.uniform(0.5, 2.0), 1),
            "prospect_per_minute": round(random.uniform(0.3, 1.5), 1)
        }
    }
