"""
AI Recommendations Service
==========================
Intelligent recommendations for sales optimization, next actions, and coaching.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import uuid
import random


class RecommendationType(str, Enum):
    """Recommendation types."""
    NEXT_BEST_ACTION = "next_best_action"
    LEAD_PRIORITIZATION = "lead_prioritization"
    DEAL_COACHING = "deal_coaching"
    EMAIL_TIMING = "email_timing"
    CONTENT_SUGGESTION = "content_suggestion"
    UPSELL_OPPORTUNITY = "upsell_opportunity"
    CROSS_SELL = "cross_sell"
    CHURN_PREVENTION = "churn_prevention"
    MEETING_PREP = "meeting_prep"
    FOLLOW_UP = "follow_up"
    OBJECTION_HANDLING = "objection_handling"
    PRICING_STRATEGY = "pricing_strategy"
    COMPETITOR_INTEL = "competitor_intel"
    QUOTA_ATTAINMENT = "quota_attainment"
    TERRITORY_OPTIMIZATION = "territory_optimization"
    SKILL_DEVELOPMENT = "skill_development"
    PIPELINE_HEALTH = "pipeline_health"
    WIN_PROBABILITY = "win_probability"
    ENGAGEMENT_TIMING = "engagement_timing"
    RELATIONSHIP_BUILDING = "relationship_building"


class RecommendationCategory(str, Enum):
    """Recommendation categories."""
    PROSPECTING = "prospecting"
    ENGAGEMENT = "engagement"
    DEAL_MANAGEMENT = "deal_management"
    RELATIONSHIP = "relationship"
    COACHING = "coaching"
    PRODUCTIVITY = "productivity"
    REVENUE = "revenue"
    RETENTION = "retention"


class RecommendationPriority(str, Enum):
    """Recommendation priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(str, Enum):
    """Recommendation status."""
    PENDING = "pending"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    EXPIRED = "expired"
    COMPLETED = "completed"


class FeedbackType(str, Enum):
    """Feedback types."""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    ALREADY_DONE = "already_done"
    NOT_APPLICABLE = "not_applicable"
    INCORRECT = "incorrect"


@dataclass
class RecommendationAction:
    """Action associated with a recommendation."""
    id: str
    label: str
    action_type: str  # "navigate", "execute", "api_call"
    action_data: dict[str, Any] = field(default_factory=dict)
    primary: bool = False


@dataclass
class RecommendationFeedback:
    """User feedback on a recommendation."""
    id: str
    recommendation_id: str
    user_id: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Recommendation:
    """AI-generated recommendation."""
    id: str
    type: RecommendationType
    category: RecommendationCategory
    priority: RecommendationPriority
    title: str
    description: str
    user_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    confidence: float = 0.0  # 0-1 confidence score
    impact_score: float = 0.0  # Expected impact 0-100
    reasoning: Optional[str] = None
    actions: list[RecommendationAction] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    status: RecommendationStatus = RecommendationStatus.PENDING
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    viewed_at: Optional[datetime] = None
    actioned_at: Optional[datetime] = None


@dataclass
class RecommendationModel:
    """Model for generating recommendations."""
    id: str
    name: str
    type: RecommendationType
    enabled: bool = True
    version: str = "1.0"
    accuracy: float = 0.0
    total_predictions: int = 0
    accepted_predictions: int = 0
    last_trained: Optional[datetime] = None


@dataclass
class InsightTrend:
    """Trend insight for analysis."""
    metric: str
    current_value: float
    previous_value: float
    change_percent: float
    trend_direction: str  # "up", "down", "stable"
    period: str
    insight: str


class RecommendationsService:
    """
    AI Recommendations service.
    
    Generates intelligent recommendations for sales optimization,
    next best actions, deal coaching, and more.
    """
    
    def __init__(self):
        """Initialize recommendations service."""
        self.recommendations: dict[str, Recommendation] = {}
        self.feedback: dict[str, RecommendationFeedback] = {}
        self.models: dict[str, RecommendationModel] = {}
        
        # Initialize default models
        self._init_models()
    
    def _init_models(self):
        """Initialize recommendation models."""
        default_models = [
            RecommendationModel(
                id="next_action_model",
                name="Next Best Action Model",
                type=RecommendationType.NEXT_BEST_ACTION,
                accuracy=0.78,
            ),
            RecommendationModel(
                id="lead_priority_model",
                name="Lead Prioritization Model",
                type=RecommendationType.LEAD_PRIORITIZATION,
                accuracy=0.82,
            ),
            RecommendationModel(
                id="win_prob_model",
                name="Win Probability Model",
                type=RecommendationType.WIN_PROBABILITY,
                accuracy=0.75,
            ),
            RecommendationModel(
                id="churn_model",
                name="Churn Prediction Model",
                type=RecommendationType.CHURN_PREVENTION,
                accuracy=0.71,
            ),
            RecommendationModel(
                id="upsell_model",
                name="Upsell Detection Model",
                type=RecommendationType.UPSELL_OPPORTUNITY,
                accuracy=0.68,
            ),
            RecommendationModel(
                id="timing_model",
                name="Engagement Timing Model",
                type=RecommendationType.ENGAGEMENT_TIMING,
                accuracy=0.73,
            ),
        ]
        
        for model in default_models:
            self.models[model.id] = model
    
    async def generate_recommendations(
        self,
        user_id: str,
        types: Optional[list[RecommendationType]] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[Recommendation]:
        """
        Generate recommendations for a user.
        
        Args:
            user_id: User ID
            types: Types of recommendations to generate
            entity_type: Specific entity type (deal, lead, etc.)
            entity_id: Specific entity ID
            limit: Maximum recommendations to generate
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if types is None:
            types = list(RecommendationType)
        
        # Generate recommendations based on type
        for rec_type in types[:limit]:
            rec = await self._generate_single_recommendation(
                user_id=user_id,
                rec_type=rec_type,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            if rec:
                recommendations.append(rec)
                self.recommendations[rec.id] = rec
        
        # Sort by priority and confidence
        recommendations.sort(
            key=lambda x: (
                list(RecommendationPriority).index(x.priority),
                -x.confidence,
            )
        )
        
        return recommendations[:limit]
    
    async def _generate_single_recommendation(
        self,
        user_id: str,
        rec_type: RecommendationType,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Optional[Recommendation]:
        """Generate a single recommendation."""
        
        # Template-based generation (would use ML models in production)
        templates = {
            RecommendationType.NEXT_BEST_ACTION: {
                "title": "Follow up with high-value prospect",
                "description": "Based on engagement patterns, now is the optimal time to reach out to this prospect.",
                "category": RecommendationCategory.ENGAGEMENT,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "Send Email", "action_type": "navigate", "primary": True},
                    {"label": "Schedule Call", "action_type": "navigate"},
                ],
            },
            RecommendationType.LEAD_PRIORITIZATION: {
                "title": "Hot lead requires immediate attention",
                "description": "This lead has shown significant buying signals in the past 24 hours.",
                "category": RecommendationCategory.PROSPECTING,
                "priority": RecommendationPriority.CRITICAL,
                "actions": [
                    {"label": "View Lead", "action_type": "navigate", "primary": True},
                    {"label": "Call Now", "action_type": "execute"},
                ],
            },
            RecommendationType.DEAL_COACHING: {
                "title": "Deal stalled - Try multi-threading",
                "description": "This deal hasn't progressed in 2 weeks. Consider engaging additional stakeholders.",
                "category": RecommendationCategory.DEAL_MANAGEMENT,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "Find Contacts", "action_type": "navigate", "primary": True},
                    {"label": "View Playbook", "action_type": "navigate"},
                ],
            },
            RecommendationType.EMAIL_TIMING: {
                "title": "Best time to send email",
                "description": "Historical data shows this contact opens emails at 9 AM on Tuesdays.",
                "category": RecommendationCategory.PRODUCTIVITY,
                "priority": RecommendationPriority.MEDIUM,
                "actions": [
                    {"label": "Schedule Email", "action_type": "navigate", "primary": True},
                ],
            },
            RecommendationType.UPSELL_OPPORTUNITY: {
                "title": "Upsell opportunity detected",
                "description": "This customer's usage patterns suggest they could benefit from the Enterprise plan.",
                "category": RecommendationCategory.REVENUE,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "Create Quote", "action_type": "navigate", "primary": True},
                    {"label": "View Usage", "action_type": "navigate"},
                ],
            },
            RecommendationType.CHURN_PREVENTION: {
                "title": "Customer at risk of churning",
                "description": "Engagement has dropped 60% in the last month. Proactive outreach recommended.",
                "category": RecommendationCategory.RETENTION,
                "priority": RecommendationPriority.CRITICAL,
                "actions": [
                    {"label": "Schedule Check-in", "action_type": "navigate", "primary": True},
                    {"label": "View Account Health", "action_type": "navigate"},
                ],
            },
            RecommendationType.MEETING_PREP: {
                "title": "Prepare for upcoming meeting",
                "description": "You have a meeting with ACME Corp in 2 hours. Review the prep materials.",
                "category": RecommendationCategory.ENGAGEMENT,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "View Prep Guide", "action_type": "navigate", "primary": True},
                    {"label": "Review History", "action_type": "navigate"},
                ],
            },
            RecommendationType.FOLLOW_UP: {
                "title": "Follow-up overdue",
                "description": "You promised to follow up 3 days ago. The prospect may be waiting.",
                "category": RecommendationCategory.ENGAGEMENT,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "Send Follow-up", "action_type": "navigate", "primary": True},
                ],
            },
            RecommendationType.WIN_PROBABILITY: {
                "title": "Deal win probability updated",
                "description": "Based on recent activity, win probability has increased to 72%.",
                "category": RecommendationCategory.DEAL_MANAGEMENT,
                "priority": RecommendationPriority.MEDIUM,
                "actions": [
                    {"label": "View Analysis", "action_type": "navigate", "primary": True},
                ],
            },
            RecommendationType.COMPETITOR_INTEL: {
                "title": "Competitor mentioned in conversation",
                "description": "The prospect mentioned evaluating CompetitorX. View battle cards.",
                "category": RecommendationCategory.DEAL_MANAGEMENT,
                "priority": RecommendationPriority.HIGH,
                "actions": [
                    {"label": "View Battle Card", "action_type": "navigate", "primary": True},
                    {"label": "Add to Notes", "action_type": "execute"},
                ],
            },
        }
        
        template = templates.get(rec_type)
        if not template:
            return None
        
        # Build actions
        actions = []
        for i, action_data in enumerate(template.get("actions", [])):
            actions.append(RecommendationAction(
                id=f"action_{i}",
                label=action_data["label"],
                action_type=action_data["action_type"],
                primary=action_data.get("primary", False),
            ))
        
        return Recommendation(
            id=str(uuid.uuid4()),
            type=rec_type,
            category=template["category"],
            priority=template["priority"],
            title=template["title"],
            description=template["description"],
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            confidence=random.uniform(0.65, 0.95),
            impact_score=random.uniform(50, 95),
            reasoning=f"Based on historical patterns and ML model predictions for {rec_type.value}",
            actions=actions,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    
    async def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        """Get a recommendation by ID."""
        return self.recommendations.get(rec_id)
    
    async def get_user_recommendations(
        self,
        user_id: str,
        status: Optional[RecommendationStatus] = None,
        category: Optional[RecommendationCategory] = None,
        priority: Optional[RecommendationPriority] = None,
        limit: int = 50,
    ) -> list[Recommendation]:
        """Get recommendations for a user."""
        recs = [
            r for r in self.recommendations.values()
            if r.user_id == user_id
        ]
        
        if status:
            recs = [r for r in recs if r.status == status]
        
        if category:
            recs = [r for r in recs if r.category == category]
        
        if priority:
            recs = [r for r in recs if r.priority == priority]
        
        # Filter expired
        now = datetime.utcnow()
        recs = [r for r in recs if not r.expires_at or r.expires_at > now]
        
        # Sort by priority and creation
        recs.sort(
            key=lambda x: (
                list(RecommendationPriority).index(x.priority),
                -x.created_at.timestamp(),
            )
        )
        
        return recs[:limit]
    
    async def mark_viewed(self, rec_id: str) -> Optional[Recommendation]:
        """Mark a recommendation as viewed."""
        rec = self.recommendations.get(rec_id)
        if rec:
            rec.status = RecommendationStatus.VIEWED
            rec.viewed_at = datetime.utcnow()
        return rec
    
    async def accept_recommendation(
        self,
        rec_id: str,
        action_id: Optional[str] = None,
    ) -> Optional[Recommendation]:
        """Accept a recommendation."""
        rec = self.recommendations.get(rec_id)
        if rec:
            rec.status = RecommendationStatus.ACCEPTED
            rec.actioned_at = datetime.utcnow()
            
            # Update model stats
            for model in self.models.values():
                if model.type == rec.type:
                    model.total_predictions += 1
                    model.accepted_predictions += 1
                    break
        
        return rec
    
    async def dismiss_recommendation(
        self,
        rec_id: str,
        reason: Optional[str] = None,
    ) -> Optional[Recommendation]:
        """Dismiss a recommendation."""
        rec = self.recommendations.get(rec_id)
        if rec:
            rec.status = RecommendationStatus.DISMISSED
            rec.actioned_at = datetime.utcnow()
            
            # Update model stats
            for model in self.models.values():
                if model.type == rec.type:
                    model.total_predictions += 1
                    break
        
        return rec
    
    async def complete_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        """Mark a recommendation as completed."""
        rec = self.recommendations.get(rec_id)
        if rec:
            rec.status = RecommendationStatus.COMPLETED
            rec.actioned_at = datetime.utcnow()
        return rec
    
    async def submit_feedback(
        self,
        rec_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        comment: Optional[str] = None,
    ) -> RecommendationFeedback:
        """Submit feedback on a recommendation."""
        feedback = RecommendationFeedback(
            id=str(uuid.uuid4()),
            recommendation_id=rec_id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment,
        )
        self.feedback[feedback.id] = feedback
        
        # Update model accuracy based on feedback
        rec = self.recommendations.get(rec_id)
        if rec:
            for model in self.models.values():
                if model.type == rec.type:
                    if feedback_type == FeedbackType.HELPFUL:
                        model.accuracy = min(1.0, model.accuracy + 0.001)
                    elif feedback_type in [FeedbackType.NOT_HELPFUL, FeedbackType.INCORRECT]:
                        model.accuracy = max(0.0, model.accuracy - 0.002)
                    break
        
        return feedback
    
    async def get_deal_recommendations(
        self,
        deal_id: str,
        user_id: str,
    ) -> list[Recommendation]:
        """Get recommendations specific to a deal."""
        deal_types = [
            RecommendationType.DEAL_COACHING,
            RecommendationType.WIN_PROBABILITY,
            RecommendationType.COMPETITOR_INTEL,
            RecommendationType.NEXT_BEST_ACTION,
            RecommendationType.OBJECTION_HANDLING,
            RecommendationType.PRICING_STRATEGY,
        ]
        
        return await self.generate_recommendations(
            user_id=user_id,
            types=deal_types,
            entity_type="deal",
            entity_id=deal_id,
            limit=5,
        )
    
    async def get_lead_recommendations(
        self,
        lead_id: str,
        user_id: str,
    ) -> list[Recommendation]:
        """Get recommendations specific to a lead."""
        lead_types = [
            RecommendationType.LEAD_PRIORITIZATION,
            RecommendationType.NEXT_BEST_ACTION,
            RecommendationType.EMAIL_TIMING,
            RecommendationType.CONTENT_SUGGESTION,
            RecommendationType.ENGAGEMENT_TIMING,
        ]
        
        return await self.generate_recommendations(
            user_id=user_id,
            types=lead_types,
            entity_type="lead",
            entity_id=lead_id,
            limit=5,
        )
    
    async def get_account_recommendations(
        self,
        account_id: str,
        user_id: str,
    ) -> list[Recommendation]:
        """Get recommendations specific to an account."""
        account_types = [
            RecommendationType.UPSELL_OPPORTUNITY,
            RecommendationType.CROSS_SELL,
            RecommendationType.CHURN_PREVENTION,
            RecommendationType.RELATIONSHIP_BUILDING,
            RecommendationType.NEXT_BEST_ACTION,
        ]
        
        return await self.generate_recommendations(
            user_id=user_id,
            types=account_types,
            entity_type="account",
            entity_id=account_id,
            limit=5,
        )
    
    async def get_coaching_insights(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Get coaching insights for a user."""
        return {
            "user_id": user_id,
            "skill_areas": [
                {"area": "Prospecting", "score": 78, "trend": "up"},
                {"area": "Discovery", "score": 85, "trend": "stable"},
                {"area": "Presenting", "score": 72, "trend": "up"},
                {"area": "Objection Handling", "score": 68, "trend": "down"},
                {"area": "Closing", "score": 75, "trend": "up"},
            ],
            "improvement_suggestions": [
                "Practice objection handling with roleplay scenarios",
                "Review successful close calls from top performers",
                "Focus on multi-threading in enterprise deals",
            ],
            "achievements": [
                "Improved discovery call rating by 12%",
                "Increased email response rate to 32%",
                "Reduced deal cycle time by 8 days",
            ],
        }
    
    async def get_pipeline_insights(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Get pipeline health insights."""
        return {
            "health_score": 72,
            "trends": [
                InsightTrend(
                    metric="Pipeline Value",
                    current_value=850000,
                    previous_value=780000,
                    change_percent=8.97,
                    trend_direction="up",
                    period="week",
                    insight="Pipeline value grew 9% this week",
                ),
                InsightTrend(
                    metric="Average Deal Size",
                    current_value=42500,
                    previous_value=38000,
                    change_percent=11.84,
                    trend_direction="up",
                    period="month",
                    insight="Average deal size increased 12%",
                ),
                InsightTrend(
                    metric="Win Rate",
                    current_value=28.5,
                    previous_value=31.2,
                    change_percent=-8.65,
                    trend_direction="down",
                    period="month",
                    insight="Win rate dropped 9% - review lost deals",
                ),
            ],
            "risks": [
                "5 deals have been stalled for >30 days",
                "3 high-value deals lack executive sponsor",
                "Pipeline coverage is 2.8x (below 3x target)",
            ],
            "opportunities": [
                "2 deals show high closing probability",
                "3 expansion opportunities identified",
                "Q4 pipeline trending 15% above target",
            ],
        }
    
    async def get_model_stats(self) -> list[dict[str, Any]]:
        """Get recommendation model statistics."""
        return [
            {
                "id": model.id,
                "name": model.name,
                "type": model.type.value,
                "accuracy": model.accuracy,
                "total_predictions": model.total_predictions,
                "accepted_predictions": model.accepted_predictions,
                "acceptance_rate": (
                    model.accepted_predictions / model.total_predictions
                    if model.total_predictions > 0 else 0
                ),
                "enabled": model.enabled,
                "version": model.version,
            }
            for model in self.models.values()
        ]
    
    async def toggle_model(self, model_id: str, enabled: bool) -> Optional[dict]:
        """Enable or disable a recommendation model."""
        model = self.models.get(model_id)
        if model:
            model.enabled = enabled
            return {"id": model.id, "enabled": model.enabled}
        return None


# Singleton instance
_recommendations_service: Optional[RecommendationsService] = None


def get_recommendations_service() -> RecommendationsService:
    """Get or create recommendations service singleton."""
    global _recommendations_service
    if _recommendations_service is None:
        _recommendations_service = RecommendationsService()
    return _recommendations_service
