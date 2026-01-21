"""
Sales Coaching Routes - Rep development and performance tracking
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

router = APIRouter(prefix="/sales-coaching", tags=["Sales Coaching"])


class SkillCategory(str, Enum):
    DISCOVERY = "discovery"
    PRESENTATION = "presentation"
    OBJECTION_HANDLING = "objection_handling"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    RELATIONSHIP_BUILDING = "relationship_building"
    PRODUCT_KNOWLEDGE = "product_knowledge"
    COMMUNICATION = "communication"
    TIME_MANAGEMENT = "time_management"


class CoachingSessionType(str, Enum):
    ONE_ON_ONE = "one_on_one"
    ROLE_PLAY = "role_play"
    CALL_REVIEW = "call_review"
    DEAL_REVIEW = "deal_review"
    SKILL_TRAINING = "skill_training"
    RIDE_ALONG = "ride_along"


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    AT_RISK = "at_risk"
    MISSED = "missed"


class CoachingPlanCreate(BaseModel):
    rep_id: str
    rep_name: str
    focus_areas: List[SkillCategory]
    start_date: str
    end_date: str
    goals: List[Dict[str, Any]]
    notes: Optional[str] = None


class CoachingSessionCreate(BaseModel):
    rep_id: str
    coach_id: str
    session_type: CoachingSessionType
    scheduled_at: str
    duration_minutes: int = 30
    focus_skills: Optional[List[SkillCategory]] = None
    agenda: Optional[str] = None
    related_deal_id: Optional[str] = None
    related_call_id: Optional[str] = None


class SkillAssessment(BaseModel):
    rep_id: str
    skill: SkillCategory
    score: int = Field(ge=1, le=10)
    notes: Optional[str] = None
    evidence: Optional[List[str]] = None


# In-memory storage
coaching_plans = {}
coaching_sessions = {}
skill_assessments = {}
coaching_notes = {}
development_goals = {}
leaderboards = {}
rep_profiles = {}
coaching_playbooks = {}


# Coaching Plans
@router.post("/plans")
async def create_coaching_plan(
    request: CoachingPlanCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create a coaching plan for a rep"""
    plan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    plan = {
        "id": plan_id,
        "rep_id": request.rep_id,
        "rep_name": request.rep_name,
        "focus_areas": [f.value for f in request.focus_areas],
        "start_date": request.start_date,
        "end_date": request.end_date,
        "goals": [
            {
                **g,
                "id": str(uuid.uuid4()),
                "status": GoalStatus.NOT_STARTED.value,
                "progress": 0
            }
            for g in request.goals
        ],
        "notes": request.notes,
        "status": "active",
        "sessions_completed": 0,
        "overall_progress": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    coaching_plans[plan_id] = plan
    
    logger.info("coaching_plan_created", plan_id=plan_id, rep_id=request.rep_id)
    return plan


@router.get("/plans")
async def list_coaching_plans(
    rep_id: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List coaching plans"""
    result = [p for p in coaching_plans.values() if p.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [p for p in result if p.get("rep_id") == rep_id]
    if status:
        result = [p for p in result if p.get("status") == status]
    
    return {"plans": result, "total": len(result)}


@router.get("/plans/{plan_id}")
async def get_coaching_plan(plan_id: str):
    """Get coaching plan details"""
    if plan_id not in coaching_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = coaching_plans[plan_id]
    sessions = [s for s in coaching_sessions.values() if s.get("plan_id") == plan_id]
    assessments = skill_assessments.get(plan["rep_id"], [])
    
    return {
        **plan,
        "sessions": sessions,
        "recent_assessments": assessments[-5:]
    }


@router.put("/plans/{plan_id}/goals/{goal_id}")
async def update_goal_progress(
    plan_id: str,
    goal_id: str,
    progress: int = Query(ge=0, le=100),
    status: Optional[GoalStatus] = None
):
    """Update goal progress"""
    if plan_id not in coaching_plans:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan = coaching_plans[plan_id]
    
    for goal in plan.get("goals", []):
        if goal.get("id") == goal_id:
            goal["progress"] = progress
            if status:
                goal["status"] = status.value
            elif progress >= 100:
                goal["status"] = GoalStatus.ACHIEVED.value
            goal["updated_at"] = datetime.utcnow().isoformat()
            break
    
    # Recalculate overall progress
    goals = plan.get("goals", [])
    if goals:
        plan["overall_progress"] = sum(g.get("progress", 0) for g in goals) // len(goals)
    
    return plan


# Coaching Sessions
@router.post("/sessions")
async def create_coaching_session(
    request: CoachingSessionCreate,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Schedule a coaching session"""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    session = {
        "id": session_id,
        "rep_id": request.rep_id,
        "coach_id": request.coach_id,
        "session_type": request.session_type.value,
        "scheduled_at": request.scheduled_at,
        "duration_minutes": request.duration_minutes,
        "focus_skills": [s.value for s in (request.focus_skills or [])],
        "agenda": request.agenda,
        "related_deal_id": request.related_deal_id,
        "related_call_id": request.related_call_id,
        "status": "scheduled",
        "notes": None,
        "action_items": [],
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    coaching_sessions[session_id] = session
    
    logger.info("coaching_session_created", session_id=session_id)
    return session


@router.get("/sessions")
async def list_coaching_sessions(
    rep_id: Optional[str] = None,
    coach_id: Optional[str] = None,
    session_type: Optional[CoachingSessionType] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """List coaching sessions"""
    result = [s for s in coaching_sessions.values() if s.get("tenant_id") == tenant_id]
    
    if rep_id:
        result = [s for s in result if s.get("rep_id") == rep_id]
    if coach_id:
        result = [s for s in result if s.get("coach_id") == coach_id]
    if session_type:
        result = [s for s in result if s.get("session_type") == session_type.value]
    if status:
        result = [s for s in result if s.get("status") == status]
    if start_date:
        result = [s for s in result if s.get("scheduled_at", "") >= start_date]
    if end_date:
        result = [s for s in result if s.get("scheduled_at", "") <= end_date]
    
    result.sort(key=lambda x: x.get("scheduled_at", ""), reverse=True)
    
    return {"sessions": result, "total": len(result)}


@router.get("/sessions/{session_id}")
async def get_coaching_session(session_id: str):
    """Get session details"""
    if session_id not in coaching_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return coaching_sessions[session_id]


@router.post("/sessions/{session_id}/complete")
async def complete_coaching_session(
    session_id: str,
    notes: str,
    action_items: List[str],
    skill_scores: Optional[Dict[str, int]] = None
):
    """Complete a coaching session"""
    if session_id not in coaching_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = coaching_sessions[session_id]
    session["status"] = "completed"
    session["notes"] = notes
    session["action_items"] = [
        {"task": item, "completed": False, "id": str(uuid.uuid4())}
        for item in action_items
    ]
    session["completed_at"] = datetime.utcnow().isoformat()
    
    # Record skill scores if provided
    if skill_scores:
        rep_id = session["rep_id"]
        if rep_id not in skill_assessments:
            skill_assessments[rep_id] = []
        
        for skill, score in skill_scores.items():
            skill_assessments[rep_id].append({
                "id": str(uuid.uuid4()),
                "skill": skill,
                "score": score,
                "session_id": session_id,
                "assessed_at": datetime.utcnow().isoformat()
            })
    
    logger.info("coaching_session_completed", session_id=session_id)
    return session


# Skill Assessments
@router.post("/assessments")
async def create_skill_assessment(
    request: SkillAssessment,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create skill assessment"""
    assessment_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    assessment = {
        "id": assessment_id,
        "rep_id": request.rep_id,
        "skill": request.skill.value,
        "score": request.score,
        "notes": request.notes,
        "evidence": request.evidence or [],
        "assessed_by": user_id,
        "tenant_id": tenant_id,
        "assessed_at": now.isoformat()
    }
    
    if request.rep_id not in skill_assessments:
        skill_assessments[request.rep_id] = []
    skill_assessments[request.rep_id].append(assessment)
    
    return assessment


@router.get("/assessments/{rep_id}")
async def get_rep_assessments(
    rep_id: str,
    skill: Optional[SkillCategory] = None,
    limit: int = Query(default=20, le=50)
):
    """Get assessments for a rep"""
    assessments = skill_assessments.get(rep_id, [])
    
    if skill:
        assessments = [a for a in assessments if a.get("skill") == skill.value]
    
    assessments.sort(key=lambda x: x.get("assessed_at", ""), reverse=True)
    
    return {"assessments": assessments[:limit], "total": len(assessments)}


@router.get("/assessments/{rep_id}/skills-matrix")
async def get_skills_matrix(rep_id: str):
    """Get skill matrix for rep"""
    assessments = skill_assessments.get(rep_id, [])
    
    # Get latest score for each skill
    skills_matrix = {}
    for skill in SkillCategory:
        skill_assessments_list = [a for a in assessments if a.get("skill") == skill.value]
        if skill_assessments_list:
            latest = max(skill_assessments_list, key=lambda x: x.get("assessed_at", ""))
            skills_matrix[skill.value] = {
                "current_score": latest.get("score"),
                "assessments_count": len(skill_assessments_list),
                "trend": calculate_skill_trend(skill_assessments_list),
                "last_assessed": latest.get("assessed_at")
            }
        else:
            skills_matrix[skill.value] = {
                "current_score": None,
                "assessments_count": 0,
                "trend": "unknown",
                "last_assessed": None
            }
    
    # Calculate overall score
    scores = [v["current_score"] for v in skills_matrix.values() if v["current_score"] is not None]
    overall_score = sum(scores) / len(scores) if scores else None
    
    return {
        "rep_id": rep_id,
        "skills": skills_matrix,
        "overall_score": round(overall_score, 1) if overall_score else None,
        "strengths": [k for k, v in skills_matrix.items() if v.get("current_score") and v["current_score"] >= 7],
        "areas_for_improvement": [k for k, v in skills_matrix.items() if v.get("current_score") and v["current_score"] < 5]
    }


# Leaderboards
@router.get("/leaderboards")
async def get_leaderboards(
    metric: str = Query(default="deals_won"),
    period: str = Query(default="month", regex="^(week|month|quarter)$"),
    tenant_id: str = Query(default="default")
):
    """Get sales leaderboards"""
    # Mock leaderboard data
    leaderboard = [
        {
            "rank": i,
            "rep_id": f"rep_{i}",
            "rep_name": f"Sales Rep {i}",
            "metric_value": random.randint(10, 100) * (6 - i) // 2,
            "change_from_last_period": random.randint(-20, 30)
        }
        for i in range(1, 11)
    ]
    
    return {
        "metric": metric,
        "period": period,
        "leaderboard": leaderboard,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.get("/leaderboards/skills")
async def get_skills_leaderboard(
    skill: SkillCategory,
    tenant_id: str = Query(default="default")
):
    """Get skills-based leaderboard"""
    reps = []
    
    for rep_id, assessments in skill_assessments.items():
        skill_scores = [a for a in assessments if a.get("skill") == skill.value]
        if skill_scores:
            latest = max(skill_scores, key=lambda x: x.get("assessed_at", ""))
            reps.append({
                "rep_id": rep_id,
                "score": latest.get("score"),
                "assessed_at": latest.get("assessed_at")
            })
    
    reps.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    for i, rep in enumerate(reps):
        rep["rank"] = i + 1
    
    return {
        "skill": skill.value,
        "leaderboard": reps[:20],
        "total_assessed": len(reps)
    }


# Coaching Playbooks
@router.post("/playbooks")
async def create_coaching_playbook(
    name: str,
    description: Optional[str] = None,
    target_skill: SkillCategory = None,
    steps: List[Dict[str, Any]] = None,
    resources: List[str] = None,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Create coaching playbook"""
    playbook_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    playbook = {
        "id": playbook_id,
        "name": name,
        "description": description,
        "target_skill": target_skill.value if target_skill else None,
        "steps": steps or [],
        "resources": resources or [],
        "usage_count": 0,
        "created_by": user_id,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    coaching_playbooks[playbook_id] = playbook
    
    return playbook


@router.get("/playbooks")
async def list_coaching_playbooks(
    skill: Optional[SkillCategory] = None,
    tenant_id: str = Query(default="default")
):
    """List coaching playbooks"""
    result = [p for p in coaching_playbooks.values() if p.get("tenant_id") == tenant_id]
    
    if skill:
        result = [p for p in result if p.get("target_skill") == skill.value]
    
    return {"playbooks": result, "total": len(result)}


# Rep Profiles
@router.get("/reps/{rep_id}/profile")
async def get_rep_profile(rep_id: str, tenant_id: str = Query(default="default")):
    """Get comprehensive rep profile"""
    if rep_id in rep_profiles:
        return rep_profiles[rep_id]
    
    # Build profile from data
    plans = [p for p in coaching_plans.values() if p.get("rep_id") == rep_id]
    sessions = [s for s in coaching_sessions.values() if s.get("rep_id") == rep_id]
    assessments = skill_assessments.get(rep_id, [])
    
    # Calculate skills
    skills_data = {}
    for skill in SkillCategory:
        skill_list = [a for a in assessments if a.get("skill") == skill.value]
        if skill_list:
            latest = max(skill_list, key=lambda x: x.get("assessed_at", ""))
            skills_data[skill.value] = latest.get("score")
    
    profile = {
        "rep_id": rep_id,
        "total_coaching_sessions": len(sessions),
        "sessions_completed": len([s for s in sessions if s.get("status") == "completed"]),
        "active_plans": len([p for p in plans if p.get("status") == "active"]),
        "skills": skills_data,
        "overall_skill_score": sum(skills_data.values()) / len(skills_data) if skills_data else None,
        "strengths": [k for k, v in skills_data.items() if v >= 7],
        "development_areas": [k for k, v in skills_data.items() if v < 5],
        "recent_sessions": sessions[-5:],
        "tenure_months": random.randint(6, 48)
    }
    
    rep_profiles[rep_id] = profile
    
    return profile


@router.get("/reps/{rep_id}/progress")
async def get_rep_progress(
    rep_id: str,
    period: str = Query(default="quarter", regex="^(month|quarter|year)$")
):
    """Get rep progress over time"""
    assessments = skill_assessments.get(rep_id, [])
    
    # Group assessments by skill and time
    progress_data = {}
    for skill in SkillCategory:
        skill_list = sorted(
            [a for a in assessments if a.get("skill") == skill.value],
            key=lambda x: x.get("assessed_at", "")
        )
        if skill_list:
            progress_data[skill.value] = {
                "first_score": skill_list[0].get("score"),
                "latest_score": skill_list[-1].get("score"),
                "improvement": skill_list[-1].get("score") - skill_list[0].get("score"),
                "assessments": len(skill_list)
            }
    
    return {
        "rep_id": rep_id,
        "period": period,
        "skill_progress": progress_data,
        "sessions_completed": len([s for s in coaching_sessions.values() if s.get("rep_id") == rep_id and s.get("status") == "completed"]),
        "goals_achieved": random.randint(3, 8),
        "total_improvement_points": sum(p.get("improvement", 0) for p in progress_data.values() if p.get("improvement", 0) > 0)
    }


# Analytics
@router.get("/analytics/team-overview")
async def get_team_coaching_overview(tenant_id: str = Query(default="default")):
    """Get team coaching overview"""
    tenant_plans = [p for p in coaching_plans.values() if p.get("tenant_id") == tenant_id]
    tenant_sessions = [s for s in coaching_sessions.values() if s.get("tenant_id") == tenant_id]
    
    return {
        "active_plans": len([p for p in tenant_plans if p.get("status") == "active"]),
        "total_sessions": len(tenant_sessions),
        "completed_sessions": len([s for s in tenant_sessions if s.get("status") == "completed"]),
        "upcoming_sessions": len([s for s in tenant_sessions if s.get("status") == "scheduled"]),
        "reps_being_coached": len(set(p.get("rep_id") for p in tenant_plans)),
        "avg_sessions_per_rep": round(len(tenant_sessions) / max(1, len(set(s.get("rep_id") for s in tenant_sessions))), 1),
        "skill_improvement_rate": 0.73,
        "coaching_completion_rate": 0.85
    }


@router.get("/analytics/skill-gaps")
async def get_team_skill_gaps(tenant_id: str = Query(default="default")):
    """Identify team skill gaps"""
    # Aggregate all assessments
    all_scores = {skill.value: [] for skill in SkillCategory}
    
    for rep_assessments in skill_assessments.values():
        for assessment in rep_assessments:
            skill = assessment.get("skill")
            if skill in all_scores:
                all_scores[skill].append(assessment.get("score", 0))
    
    skill_averages = {
        skill: round(sum(scores) / len(scores), 1) if scores else None
        for skill, scores in all_scores.items()
    }
    
    gaps = [
        {"skill": skill, "avg_score": score, "reps_below_threshold": len([s for s in all_scores[skill] if s < 5])}
        for skill, score in skill_averages.items()
        if score is not None and score < 6
    ]
    
    return {
        "skill_averages": skill_averages,
        "identified_gaps": sorted(gaps, key=lambda x: x["avg_score"]),
        "recommended_focus_areas": [g["skill"] for g in sorted(gaps, key=lambda x: x["avg_score"])[:3]]
    }


# Helper functions
def calculate_skill_trend(assessments: List[Dict]) -> str:
    """Calculate trend for a skill"""
    if len(assessments) < 2:
        return "stable"
    
    sorted_assessments = sorted(assessments, key=lambda x: x.get("assessed_at", ""))
    recent = sorted_assessments[-1].get("score", 0)
    previous = sorted_assessments[-2].get("score", 0)
    
    if recent > previous:
        return "improving"
    elif recent < previous:
        return "declining"
    return "stable"
