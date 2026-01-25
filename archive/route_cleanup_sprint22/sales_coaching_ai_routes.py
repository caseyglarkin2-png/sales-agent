"""
Sales Coaching AI Routes - AI-powered coaching and performance improvement
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

router = APIRouter(prefix="/coaching-ai", tags=["Sales Coaching AI"])


class CoachingType(str, Enum):
    DEAL_COACHING = "deal_coaching"
    SKILL_COACHING = "skill_coaching"
    BEHAVIORAL_COACHING = "behavioral_coaching"
    PERFORMANCE_COACHING = "performance_coaching"
    ONBOARDING = "onboarding"


class SkillCategory(str, Enum):
    DISCOVERY = "discovery"
    PRESENTATION = "presentation"
    NEGOTIATION = "negotiation"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"
    RELATIONSHIP_BUILDING = "relationship_building"
    PRODUCT_KNOWLEDGE = "product_knowledge"
    PROSPECTING = "prospecting"


class CoachingStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class CoachingPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# In-memory storage
coaching_sessions = {}
skill_assessments = {}
development_plans = {}
coaching_content = {}


class CoachingSessionCreate(BaseModel):
    rep_id: str
    rep_name: str
    coaching_type: CoachingType
    focus_areas: List[SkillCategory]
    deal_id: Optional[str] = None
    notes: Optional[str] = None


class SkillAssessmentCreate(BaseModel):
    rep_id: str
    rep_name: str
    skill: SkillCategory
    score: int = Field(..., ge=1, le=10)
    assessor: str
    notes: Optional[str] = None


class DevelopmentPlanCreate(BaseModel):
    rep_id: str
    rep_name: str
    goals: List[str]
    target_skills: List[SkillCategory]
    duration_weeks: int = 12


# Real-time Coaching
@router.get("/realtime/{deal_id}")
async def get_realtime_coaching(
    deal_id: str,
    context: str = Query(default="general"),
    tenant_id: str = Query(default="default")
):
    """Get real-time AI coaching suggestions for a deal"""
    return {
        "deal_id": deal_id,
        "context": context,
        "generated_at": datetime.utcnow().isoformat(),
        "coaching_insights": [
            {
                "type": "opportunity",
                "insight": "Stakeholder engagement is low - only 2 contacts touched",
                "action": "Map the buying committee and identify 2-3 additional stakeholders",
                "priority": CoachingPriority.HIGH.value,
                "skill_area": SkillCategory.RELATIONSHIP_BUILDING.value
            },
            {
                "type": "risk",
                "insight": "Deal has been in current stage for 15 days without activity",
                "action": "Schedule next meeting or send value-reinforcing content",
                "priority": CoachingPriority.HIGH.value,
                "skill_area": SkillCategory.CLOSING.value
            },
            {
                "type": "suggestion",
                "insight": "Competitor mentioned in notes but no battlecard attached",
                "action": "Review competitive positioning and add relevant battlecard",
                "priority": CoachingPriority.MEDIUM.value,
                "skill_area": SkillCategory.PRODUCT_KNOWLEDGE.value
            }
        ],
        "recommended_questions": [
            "What's changed since our last conversation?",
            "Who else needs to be involved in this decision?",
            "What would make this a no-brainer decision?",
            "What's your timeline for making a decision?"
        ],
        "objection_prep": [
            {
                "likely_objection": "Your pricing is higher than competitors",
                "suggested_response": "Let's look at the total value delivered. Our customers see an average 3x ROI within 6 months..."
            }
        ]
    }


# Call Analysis
@router.post("/analyze-call")
async def analyze_call(
    call_id: Optional[str] = None,
    call_transcript: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Analyze a sales call and provide coaching feedback"""
    return {
        "call_id": call_id or str(uuid.uuid4()),
        "analyzed_at": datetime.utcnow().isoformat(),
        "talk_ratio": {
            "rep_talk_time": round(random.uniform(0.35, 0.55), 2),
            "customer_talk_time": round(random.uniform(0.45, 0.65), 2),
            "ideal_rep_ratio": 0.40,
            "assessment": random.choice(["optimal", "too_much_talking", "good"])
        },
        "question_analysis": {
            "open_questions": random.randint(5, 15),
            "closed_questions": random.randint(3, 10),
            "discovery_questions": random.randint(3, 12),
            "assessment": random.choice(["excellent", "good", "needs_improvement"])
        },
        "sentiment": {
            "customer_sentiment": random.choice(["positive", "neutral", "mixed"]),
            "engagement_level": random.choice(["high", "medium", "low"]),
            "buying_signals_detected": random.randint(0, 5)
        },
        "coaching_feedback": [
            {
                "category": SkillCategory.DISCOVERY.value,
                "score": random.randint(6, 10),
                "feedback": "Good use of open-ended questions to uncover pain points",
                "improvement": "Try to dig deeper on the business impact"
            },
            {
                "category": SkillCategory.OBJECTION_HANDLING.value,
                "score": random.randint(5, 9),
                "feedback": "Handled the pricing objection adequately",
                "improvement": "Use more specific ROI examples from similar customers"
            },
            {
                "category": SkillCategory.CLOSING.value,
                "score": random.randint(5, 8),
                "feedback": "Clear next steps established",
                "improvement": "Consider asking for a specific commitment at call end"
            }
        ],
        "key_moments": [
            {"timestamp": "5:32", "moment": "Customer expressed frustration with current solution", "type": "opportunity"},
            {"timestamp": "12:45", "moment": "Pricing objection raised", "type": "objection"},
            {"timestamp": "18:20", "moment": "Customer agreed to follow-up demo", "type": "commitment"}
        ]
    }


# Skill Assessment
@router.post("/skills/assess")
async def create_skill_assessment(
    request: SkillAssessmentCreate,
    tenant_id: str = Query(default="default")
):
    """Create a skill assessment for a rep"""
    assessment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    assessment = {
        "id": assessment_id,
        "rep_id": request.rep_id,
        "rep_name": request.rep_name,
        "skill": request.skill.value,
        "score": request.score,
        "assessor": request.assessor,
        "notes": request.notes,
        "tenant_id": tenant_id,
        "assessed_at": now.isoformat()
    }
    
    skill_assessments[assessment_id] = assessment
    
    return assessment


@router.get("/skills/{rep_id}")
async def get_rep_skills(
    rep_id: str,
    tenant_id: str = Query(default="default")
):
    """Get skill profile for a rep"""
    skills = []
    for skill in SkillCategory:
        skills.append({
            "skill": skill.value,
            "current_score": random.randint(5, 10),
            "target_score": 8,
            "trend": random.choice(["improving", "stable", "declining"]),
            "assessments_count": random.randint(1, 5),
            "last_assessed": (datetime.utcnow() - timedelta(days=random.randint(7, 60))).isoformat()
        })
    
    return {
        "rep_id": rep_id,
        "skill_profile": skills,
        "overall_score": round(random.uniform(6.5, 8.5), 1),
        "strongest_skill": random.choice([s.value for s in SkillCategory]),
        "development_areas": random.sample([s.value for s in SkillCategory], 2),
        "peer_comparison_percentile": random.randint(40, 90)
    }


# Coaching Sessions
@router.post("/sessions")
async def create_coaching_session(
    request: CoachingSessionCreate,
    tenant_id: str = Query(default="default")
):
    """Create a coaching session"""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    session = {
        "id": session_id,
        "rep_id": request.rep_id,
        "rep_name": request.rep_name,
        "coaching_type": request.coaching_type.value,
        "focus_areas": [f.value for f in request.focus_areas],
        "deal_id": request.deal_id,
        "notes": request.notes,
        "status": CoachingStatus.ASSIGNED.value,
        "action_items": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "scheduled_for": (now + timedelta(days=random.randint(1, 7))).isoformat()
    }
    
    coaching_sessions[session_id] = session
    
    return session


@router.get("/sessions")
async def list_coaching_sessions(
    rep_id: Optional[str] = None,
    status: Optional[CoachingStatus] = None,
    coaching_type: Optional[CoachingType] = None,
    tenant_id: str = Query(default="default")
):
    """List coaching sessions"""
    result = [s for s in coaching_sessions.values() if s.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [s for s in result if s.get("rep_id") == rep_id]
    if status:
        result = [s for s in result if s.get("status") == status.value]
    if coaching_type:
        result = [s for s in result if s.get("coaching_type") == coaching_type.value]
    
    return {"sessions": result, "total": len(result)}


@router.post("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    outcomes: List[str] = [],
    action_items: List[str] = [],
    tenant_id: str = Query(default="default")
):
    """Complete a coaching session"""
    session = coaching_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session["status"] = CoachingStatus.COMPLETED.value
    session["completed_at"] = datetime.utcnow().isoformat()
    session["outcomes"] = outcomes
    session["action_items"] = action_items
    
    return session


# Development Plans
@router.post("/development-plans")
async def create_development_plan(
    request: DevelopmentPlanCreate,
    tenant_id: str = Query(default="default")
):
    """Create a development plan for a rep"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    milestones = []
    for i, skill in enumerate(request.target_skills):
        milestones.append({
            "id": str(uuid.uuid4()),
            "skill": skill.value,
            "target_improvement": random.randint(1, 3),
            "target_date": (now + timedelta(weeks=(i + 1) * (request.duration_weeks // len(request.target_skills)))).isoformat(),
            "status": "not_started"
        })
    
    plan = {
        "id": plan_id,
        "rep_id": request.rep_id,
        "rep_name": request.rep_name,
        "goals": request.goals,
        "target_skills": [s.value for s in request.target_skills],
        "duration_weeks": request.duration_weeks,
        "milestones": milestones,
        "status": "active",
        "progress_pct": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "target_completion": (now + timedelta(weeks=request.duration_weeks)).isoformat()
    }
    
    development_plans[plan_id] = plan
    
    return plan


@router.get("/development-plans/{rep_id}")
async def get_rep_development_plan(
    rep_id: str,
    tenant_id: str = Query(default="default")
):
    """Get development plan for a rep"""
    plans = [p for p in development_plans.values() 
             if p.get("rep_id") == rep_id and p.get("tenant_id") == tenant_id]
    
    if not plans:
        # Return mock plan
        return {
            "rep_id": rep_id,
            "goals": ["Improve discovery skills", "Close larger deals", "Build executive relationships"],
            "target_skills": [SkillCategory.DISCOVERY.value, SkillCategory.CLOSING.value, SkillCategory.RELATIONSHIP_BUILDING.value],
            "progress_pct": random.randint(20, 70),
            "status": "active",
            "milestones": [
                {"skill": SkillCategory.DISCOVERY.value, "target_improvement": 2, "status": "completed", "actual_improvement": 2},
                {"skill": SkillCategory.CLOSING.value, "target_improvement": 2, "status": "in_progress", "current_improvement": 1},
                {"skill": SkillCategory.RELATIONSHIP_BUILDING.value, "target_improvement": 1, "status": "not_started"}
            ],
            "recommended_content": [
                {"title": "Advanced Discovery Techniques", "type": "course", "duration_min": 45},
                {"title": "Closing with Confidence", "type": "workshop", "duration_min": 90},
                {"title": "Executive Communication Masterclass", "type": "video", "duration_min": 30}
            ]
        }
    
    return plans[0]


# AI Recommendations
@router.get("/recommendations/{rep_id}")
async def get_coaching_recommendations(
    rep_id: str,
    tenant_id: str = Query(default="default")
):
    """Get AI-generated coaching recommendations for a rep"""
    return {
        "rep_id": rep_id,
        "generated_at": datetime.utcnow().isoformat(),
        "performance_summary": {
            "quota_attainment": round(random.uniform(0.70, 1.20), 2),
            "win_rate": round(random.uniform(0.25, 0.45), 2),
            "avg_deal_size": random.randint(40000, 100000),
            "activity_score": random.randint(60, 95)
        },
        "focus_areas": [
            {
                "area": SkillCategory.DISCOVERY.value,
                "priority": CoachingPriority.HIGH.value,
                "current_score": random.randint(5, 7),
                "target_score": 8,
                "rationale": "Deals often stall after initial discovery - deeper qualification needed",
                "suggested_actions": [
                    "Complete advanced discovery training module",
                    "Shadow top performer discovery calls",
                    "Role-play discovery scenarios with manager"
                ]
            },
            {
                "area": SkillCategory.OBJECTION_HANDLING.value,
                "priority": CoachingPriority.MEDIUM.value,
                "current_score": random.randint(5, 7),
                "target_score": 8,
                "rationale": "Price objections leading to discounting more than peers",
                "suggested_actions": [
                    "Review objection handling playbook",
                    "Practice value-based responses",
                    "Analyze successful competitor response examples"
                ]
            }
        ],
        "peer_insights": {
            "compared_to_peers": random.choice(["above_average", "average", "below_average"]),
            "top_performer_differentiators": [
                "More thorough discovery questions",
                "Stronger executive relationships",
                "Better objection handling"
            ]
        },
        "recommended_sessions": [
            {
                "type": CoachingType.SKILL_COACHING.value,
                "focus": SkillCategory.DISCOVERY.value,
                "frequency": "weekly",
                "duration_min": 30
            },
            {
                "type": CoachingType.DEAL_COACHING.value,
                "focus": "Pipeline review",
                "frequency": "bi-weekly",
                "duration_min": 45
            }
        ]
    }


# Team Overview
@router.get("/team/{manager_id}")
async def get_team_coaching_overview(
    manager_id: str,
    tenant_id: str = Query(default="default")
):
    """Get coaching overview for a manager's team"""
    team_members = []
    for i in range(random.randint(5, 10)):
        team_members.append({
            "rep_id": f"rep_{i}",
            "rep_name": f"Sales Rep {i + 1}",
            "overall_skill_score": round(random.uniform(5.5, 8.5), 1),
            "coaching_sessions_completed": random.randint(2, 10),
            "development_progress_pct": random.randint(20, 80),
            "priority_focus_area": random.choice([s.value for s in SkillCategory]),
            "last_coaching_date": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
        })
    
    return {
        "manager_id": manager_id,
        "team_size": len(team_members),
        "team_members": team_members,
        "team_averages": {
            "skill_score": round(random.uniform(6.5, 7.5), 1),
            "development_progress": random.randint(40, 60),
            "sessions_per_rep": round(random.uniform(4, 8), 1)
        },
        "coaching_priorities": [
            {"skill": SkillCategory.DISCOVERY.value, "team_gap": round(random.uniform(1, 2), 1), "reps_needing_focus": random.randint(2, 5)},
            {"skill": SkillCategory.CLOSING.value, "team_gap": round(random.uniform(0.5, 1.5), 1), "reps_needing_focus": random.randint(1, 4)}
        ],
        "suggested_team_trainings": [
            {"topic": "Advanced Discovery Techniques", "recommended_for": random.randint(3, 6), "format": "workshop"},
            {"topic": "Negotiation Masterclass", "recommended_for": random.randint(2, 5), "format": "training"}
        ]
    }


# Content Library
@router.get("/content")
async def get_coaching_content(
    skill: Optional[SkillCategory] = None,
    content_type: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get coaching content library"""
    content = [
        {
            "id": str(uuid.uuid4()),
            "title": "Discovery Call Mastery",
            "type": "course",
            "skill": SkillCategory.DISCOVERY.value,
            "duration_min": 60,
            "difficulty": "intermediate",
            "rating": round(random.uniform(4.0, 5.0), 1),
            "completions": random.randint(50, 200)
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Handling Price Objections",
            "type": "video",
            "skill": SkillCategory.OBJECTION_HANDLING.value,
            "duration_min": 15,
            "difficulty": "beginner",
            "rating": round(random.uniform(4.0, 5.0), 1),
            "completions": random.randint(80, 300)
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Closing Techniques Workshop",
            "type": "workshop",
            "skill": SkillCategory.CLOSING.value,
            "duration_min": 120,
            "difficulty": "advanced",
            "rating": round(random.uniform(4.2, 5.0), 1),
            "completions": random.randint(30, 100)
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Building Executive Relationships",
            "type": "course",
            "skill": SkillCategory.RELATIONSHIP_BUILDING.value,
            "duration_min": 45,
            "difficulty": "intermediate",
            "rating": round(random.uniform(4.0, 4.8), 1),
            "completions": random.randint(40, 150)
        }
    ]
    
    if skill:
        content = [c for c in content if c.get("skill") == skill.value]
    if content_type:
        content = [c for c in content if c.get("type") == content_type]
    
    return {"content": content, "total": len(content)}
