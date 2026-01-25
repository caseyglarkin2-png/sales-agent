"""
Sales Playbook AI Routes - AI-powered playbook recommendations and execution
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

router = APIRouter(prefix="/playbook-ai", tags=["Sales Playbook AI"])


class PlaybookType(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    DEMO = "demo"
    OBJECTION_HANDLING = "objection_handling"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    EXPANSION = "expansion"
    RENEWAL = "renewal"


class DealContext(str, Enum):
    NEW_BUSINESS = "new_business"
    EXPANSION = "expansion"
    RENEWAL = "renewal"
    WIN_BACK = "win_back"


class StepType(str, Enum):
    TALK_TRACK = "talk_track"
    QUESTION = "question"
    DEMO_SCRIPT = "demo_script"
    EMAIL_TEMPLATE = "email_template"
    CALL_SCRIPT = "call_script"
    RESOURCE = "resource"
    CHECKPOINT = "checkpoint"


# In-memory storage
playbook_definitions = {}
playbook_executions = {}
playbook_recommendations = {}
ai_insights = {}


class PlaybookStepCreate(BaseModel):
    step_type: StepType
    title: str
    content: str
    order: int
    duration_minutes: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None


class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    playbook_type: PlaybookType
    deal_context: DealContext = DealContext.NEW_BUSINESS
    industry: Optional[str] = None
    company_size: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    success_metrics: Optional[Dict[str, Any]] = None


class PlaybookExecutionCreate(BaseModel):
    playbook_id: str
    deal_id: str
    rep_id: str


# AI Recommendations
@router.post("/recommend")
async def get_playbook_recommendations(
    deal_id: str,
    current_stage: str,
    deal_context: Optional[DealContext] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-recommended playbooks for a deal"""
    recommendations = [
        {
            "playbook_id": str(uuid.uuid4()),
            "name": "Enterprise Discovery Excellence",
            "type": PlaybookType.DISCOVERY.value,
            "match_score": round(random.uniform(0.85, 0.98), 2),
            "match_reasons": [
                "Matches industry profile",
                "Appropriate for company size",
                "High success rate for similar deals"
            ],
            "expected_outcomes": {
                "qualification_rate": 0.75,
                "avg_days_saved": 5,
                "success_rate": 0.68
            },
            "key_differentiators": [
                "Multi-stakeholder engagement",
                "ROI-focused approach",
                "Technical validation included"
            ]
        },
        {
            "playbook_id": str(uuid.uuid4()),
            "name": "Value-Based Selling Framework",
            "type": PlaybookType.QUALIFICATION.value,
            "match_score": round(random.uniform(0.75, 0.90), 2),
            "match_reasons": [
                "Strong win rate for this segment",
                "Addresses common objections"
            ],
            "expected_outcomes": {
                "qualification_rate": 0.70,
                "avg_days_saved": 3,
                "success_rate": 0.62
            },
            "key_differentiators": [
                "Business value quantification",
                "Executive alignment focus"
            ]
        },
        {
            "playbook_id": str(uuid.uuid4()),
            "name": "Competitive Displacement Playbook",
            "type": PlaybookType.NEGOTIATION.value,
            "match_score": round(random.uniform(0.65, 0.80), 2),
            "match_reasons": [
                "Effective against known competitor"
            ],
            "expected_outcomes": {
                "qualification_rate": 0.65,
                "avg_days_saved": 2,
                "success_rate": 0.55
            },
            "key_differentiators": [
                "Competitor-specific battlecards",
                "Switching cost analysis"
            ]
        }
    ]
    
    return {
        "deal_id": deal_id,
        "current_stage": current_stage,
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }


# Dynamic Next Steps
@router.get("/next-steps/{deal_id}")
async def get_dynamic_next_steps(
    deal_id: str,
    current_stage: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-generated next steps for a deal"""
    return {
        "deal_id": deal_id,
        "current_stage": current_stage or "discovery",
        "next_steps": [
            {
                "priority": 1,
                "action": "Schedule technical deep-dive",
                "description": "Prospect mentioned integration concerns. Schedule call with SE.",
                "talk_track": "Based on your integration requirements, I'd like to bring in our solutions engineer for a technical discussion...",
                "expected_outcome": "Technical validation",
                "suggested_timing": "Within 3 days"
            },
            {
                "priority": 2,
                "action": "Send case study",
                "description": "Share relevant case study from similar company",
                "resource_id": "case_study_acme",
                "template_id": "case_study_email",
                "expected_outcome": "Build credibility",
                "suggested_timing": "Today"
            },
            {
                "priority": 3,
                "action": "Map buying committee",
                "description": "Only 2 stakeholders identified. Need more multi-threading.",
                "talk_track": "To ensure we address everyone's needs, who else should be involved in this evaluation?",
                "expected_outcome": "Identify 2-3 more stakeholders",
                "suggested_timing": "In next meeting"
            },
            {
                "priority": 4,
                "action": "Discuss timeline",
                "description": "No close date established. Need to create urgency.",
                "talk_track": "What's driving your timeline for making a decision? Are there any upcoming initiatives this ties into?",
                "expected_outcome": "Establish target close date",
                "suggested_timing": "In next meeting"
            }
        ],
        "insights": [
            "Champion engagement is strong - leverage for internal advocacy",
            "Budget appears approved but not allocated",
            "Competition mentioned - address proactively"
        ]
    }


# Talk Tracks
@router.get("/talk-tracks")
async def get_talk_tracks(
    situation: str,
    stage: Optional[str] = None,
    industry: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-generated talk tracks for specific situations"""
    return {
        "situation": situation,
        "talk_tracks": [
            {
                "id": str(uuid.uuid4()),
                "name": "Value Discovery Opening",
                "script": """
                Thanks for making time today. Before we dive in, I'd love to understand more about what prompted you to explore [solution category].
                
                Specifically:
                - What challenges are you facing today?
                - What would success look like for you?
                - Who else is involved in this initiative?
                """,
                "tips": [
                    "Listen more than talk (aim for 70/30)",
                    "Take notes on pain points for later",
                    "Probe deeper on emotional responses"
                ],
                "success_rate": 0.72,
                "situations": ["discovery", "first_meeting"]
            },
            {
                "id": str(uuid.uuid4()),
                "name": "ROI Discussion Framework",
                "script": """
                Based on what you've shared, let me walk through the potential impact:
                
                Currently, you're spending [X hours/dollars] on [process].
                With our solution, similar companies have reduced that by [Y%].
                
                Over 12 months, that's approximately [Z] in savings/gains.
                
                Does that align with what you'd expect?
                """,
                "tips": [
                    "Use their numbers when possible",
                    "Be conservative on estimates",
                    "Connect to their stated goals"
                ],
                "success_rate": 0.68,
                "situations": ["value_justification", "proposal"]
            }
        ],
        "related_resources": [
            {"type": "battlecard", "name": "ROI Calculator", "id": "resource_123"},
            {"type": "case_study", "name": "Similar Company Success Story", "id": "resource_456"}
        ]
    }


# Objection Responses
@router.post("/objection-response")
async def get_objection_response(
    objection: str,
    deal_context: Optional[Dict[str, Any]] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-powered objection handling response"""
    return {
        "objection": objection,
        "category": random.choice(["price", "timing", "competition", "need", "authority"]),
        "responses": [
            {
                "approach": "Acknowledge and Redirect",
                "response": f"I completely understand that concern about {objection.lower()[:30]}. Many of our most successful customers felt the same way initially. What helped them was...",
                "effectiveness": 0.78,
                "next_action": "Share relevant proof point"
            },
            {
                "approach": "Quantify and Compare",
                "response": "That's an important consideration. Let me help put this in perspective. When you factor in [specific value drivers], most customers see a return within [timeframe]...",
                "effectiveness": 0.72,
                "next_action": "Walk through ROI calculation"
            },
            {
                "approach": "Isolate and Confirm",
                "response": "If we could address this concern, would you be ready to move forward? Let me explain how we've helped others in your situation...",
                "effectiveness": 0.65,
                "next_action": "Address specific concern directly"
            }
        ],
        "supporting_materials": [
            {"type": "case_study", "title": "How Acme overcame similar concerns"},
            {"type": "roi_calculator", "title": "Custom ROI Analysis"},
            {"type": "testimonial", "title": "Video testimonial from similar customer"}
        ],
        "avoid": [
            "Don't get defensive",
            "Don't offer discounts immediately",
            "Don't dismiss the concern"
        ]
    }


# Call Preparation
@router.get("/call-prep/{deal_id}")
async def prepare_for_call(
    deal_id: str,
    call_type: str = Query(default="discovery"),
    tenant_id: str = Query(default="default")
):
    """Get AI-generated call preparation guide"""
    return {
        "deal_id": deal_id,
        "call_type": call_type,
        "prep_time_minutes": 15,
        "attendees": [
            {"name": "Sarah Johnson", "title": "VP Sales", "role": "Champion", "key_interests": ["productivity", "team adoption"]},
            {"name": "Mike Chen", "title": "CFO", "role": "Economic Buyer", "key_interests": ["ROI", "cost reduction"]}
        ],
        "agenda": [
            {"topic": "Brief introductions", "duration_minutes": 5, "owner": "rep"},
            {"topic": "Recap of progress and goals", "duration_minutes": 5, "owner": "rep"},
            {"topic": "Deep dive: [specific topic]", "duration_minutes": 20, "owner": "both"},
            {"topic": "Q&A and next steps", "duration_minutes": 10, "owner": "both"}
        ],
        "key_questions_to_ask": [
            "What's changed since our last conversation?",
            "Who else should be involved in this evaluation?",
            "What would make this a clear win for you and your team?",
            "What's your timeline for making a decision?"
        ],
        "talking_points": [
            "Reference their Q1 revenue goals mentioned in last call",
            "Address integration concern from email thread",
            "Share case study from similar company"
        ],
        "watch_outs": [
            "CFO may raise budget timing concerns",
            "Technical questions about API limits expected"
        ],
        "materials_to_have_ready": [
            "Custom ROI analysis",
            "Integration architecture diagram",
            "Pricing proposal"
        ],
        "success_criteria": [
            "Confirm budget is allocated",
            "Get commitment on next steps",
            "Identify remaining stakeholders"
        ]
    }


# Email Suggestions
@router.post("/email-suggest")
async def suggest_email_content(
    deal_id: str,
    email_type: str,
    context: Optional[Dict[str, Any]] = None,
    tenant_id: str = Query(default="default")
):
    """Get AI-suggested email content"""
    return {
        "deal_id": deal_id,
        "email_type": email_type,
        "suggestions": [
            {
                "subject_lines": [
                    "Quick follow-up: [Company] x [Your Company]",
                    "Resources for your evaluation",
                    "Next steps for [initiative name]"
                ],
                "body": """
Hi [Name],

Thank you for your time today. I really enjoyed learning about [specific topic discussed].

As promised, I'm sharing:
- [Resource 1] - This addresses your question about [topic]
- [Resource 2] - Case study from a company similar to yours

Based on our discussion, I believe we can help you [achieve specific outcome] by [specific timeframe].

Would [date/time] work for a follow-up to discuss [next topic]?

Best,
[Your name]
                """,
                "personalization_opportunities": [
                    "Reference specific pain point from call",
                    "Mention mutual connection if applicable",
                    "Include relevant industry stat"
                ]
            }
        ],
        "tips": [
            "Keep under 150 words for higher response rate",
            "Include clear call-to-action",
            "Reference something specific from last interaction"
        ],
        "best_send_time": "Tuesday 10:30 AM (recipient's timezone)"
    }


# Playbook Definitions
@router.post("/playbooks")
async def create_playbook(
    request: PlaybookCreate,
    tenant_id: str = Query(default="default")
):
    """Create a new playbook"""
    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    playbook = {
        "id": playbook_id,
        "name": request.name,
        "description": request.description,
        "playbook_type": request.playbook_type.value,
        "deal_context": request.deal_context.value,
        "industry": request.industry,
        "company_size": request.company_size,
        "steps": request.steps,
        "success_metrics": request.success_metrics or {},
        "times_used": 0,
        "success_rate": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    playbook_definitions[playbook_id] = playbook
    
    return playbook


@router.get("/playbooks")
async def list_playbooks(
    playbook_type: Optional[PlaybookType] = None,
    deal_context: Optional[DealContext] = None,
    tenant_id: str = Query(default="default")
):
    """List all playbooks"""
    result = [p for p in playbook_definitions.values() if p.get("tenant_id") == tenant_id]
    
    if playbook_type:
        result = [p for p in result if p.get("playbook_type") == playbook_type.value]
    if deal_context:
        result = [p for p in result if p.get("deal_context") == deal_context.value]
    
    return {"playbooks": result, "total": len(result)}


# Analytics
@router.get("/analytics")
async def get_playbook_analytics(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get playbook performance analytics"""
    return {
        "period_days": days,
        "summary": {
            "total_executions": random.randint(100, 500),
            "unique_playbooks_used": random.randint(10, 30),
            "avg_success_rate": round(random.uniform(0.55, 0.75), 2),
            "total_deals_influenced": random.randint(50, 200)
        },
        "top_performing_playbooks": [
            {
                "name": "Enterprise Discovery",
                "executions": random.randint(20, 80),
                "success_rate": round(random.uniform(0.65, 0.85), 2),
                "avg_deal_value": random.randint(50000, 200000)
            },
            {
                "name": "Value-Based Qualification",
                "executions": random.randint(15, 60),
                "success_rate": round(random.uniform(0.60, 0.80), 2),
                "avg_deal_value": random.randint(30000, 150000)
            }
        ],
        "talk_track_effectiveness": [
            {"name": "Discovery Opening", "usage": random.randint(100, 300), "effectiveness": 0.72},
            {"name": "ROI Framework", "usage": random.randint(80, 250), "effectiveness": 0.68},
            {"name": "Objection Handler", "usage": random.randint(50, 150), "effectiveness": 0.65}
        ],
        "improvement_suggestions": [
            "Qualification playbook needs update - win rate declined 5%",
            "Add more talk tracks for pricing objections",
            "Top performers use Discovery playbook 2x more"
        ]
    }
