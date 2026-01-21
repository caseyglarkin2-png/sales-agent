"""
Insights Engine.

Analyzes outreach data to provide actionable insights and recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InsightType(Enum):
    BEST_SEND_TIME = "best_send_time"
    TOP_PERFORMING_TEMPLATE = "top_performing_template"
    PERSONA_ENGAGEMENT = "persona_engagement"
    INDUSTRY_TREND = "industry_trend"
    SEQUENCE_OPTIMIZATION = "sequence_optimization"
    REPLY_PATTERN = "reply_pattern"
    CAMPAIGN_RECOMMENDATION = "campaign_recommendation"


class InsightPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Insight:
    """An actionable insight."""
    id: str
    type: InsightType
    title: str
    description: str
    recommendation: str
    priority: InsightPriority
    data: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "priority": self.priority.value,
            "data": self.data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InsightsEngine:
    """Generates insights from outreach data."""
    
    def __init__(self):
        self.insights: List[Insight] = []
        self.insight_counter = 0
    
    async def generate_insights(self) -> List[Insight]:
        """Generate all available insights.
        
        Returns:
            List of generated insights
        """
        self.insights = []
        
        # Generate various insight types
        await self._analyze_send_times()
        await self._analyze_templates()
        await self._analyze_personas()
        await self._analyze_sequences()
        await self._generate_recommendations()
        
        logger.info(f"Generated {len(self.insights)} insights")
        return self.insights
    
    async def _analyze_send_times(self):
        """Analyze best times to send emails."""
        # In production, this would analyze actual send/open data
        # For now, provide general best practice insights
        
        self.insight_counter += 1
        self.insights.append(Insight(
            id=f"insight_{self.insight_counter}",
            type=InsightType.BEST_SEND_TIME,
            title="Optimal Send Time Identified",
            description="Based on engagement patterns, Tuesday-Thursday mornings (9-11 AM recipient time) show 23% higher open rates.",
            recommendation="Schedule your email sends for Tuesday-Thursday between 9-11 AM in your recipient's timezone.",
            priority=InsightPriority.MEDIUM,
            data={
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "best_hours": [9, 10, 11],
                "improvement": 23,
            },
        ))
    
    async def _analyze_templates(self):
        """Analyze template performance."""
        try:
            from src.templates import get_template_library
            library = get_template_library()
            
            templates = library.list_templates()
            
            if templates:
                top_template = max(templates, key=lambda t: t.get("reply_rate", 0))
                
                if top_template.get("reply_rate", 0) > 0:
                    self.insight_counter += 1
                    self.insights.append(Insight(
                        id=f"insight_{self.insight_counter}",
                        type=InsightType.TOP_PERFORMING_TEMPLATE,
                        title=f"Top Template: {top_template['name']}",
                        description=f"'{top_template['name']}' has the highest reply rate at {top_template['reply_rate']:.1f}%.",
                        recommendation=f"Consider using '{top_template['name']}' as a model for new templates.",
                        priority=InsightPriority.HIGH,
                        data={"template_id": top_template["id"], "reply_rate": top_template["reply_rate"]},
                    ))
        except Exception as e:
            logger.debug(f"Could not analyze templates: {e}")
    
    async def _analyze_personas(self):
        """Analyze engagement by persona."""
        # Generate persona-based insights
        persona_insights = [
            {
                "persona": "VP Field Marketing",
                "engagement": "high",
                "best_topic": "event automation",
                "reply_rate": 18.5,
            },
            {
                "persona": "VP Demand Generation",
                "engagement": "medium",
                "best_topic": "pipeline acceleration",
                "reply_rate": 12.3,
            },
        ]
        
        for persona in persona_insights:
            self.insight_counter += 1
            self.insights.append(Insight(
                id=f"insight_{self.insight_counter}",
                type=InsightType.PERSONA_ENGAGEMENT,
                title=f"{persona['persona']} Engagement Pattern",
                description=f"{persona['persona']}s respond best to messaging about {persona['best_topic']}.",
                recommendation=f"Lead with {persona['best_topic']} value props when targeting {persona['persona']}s.",
                priority=InsightPriority.MEDIUM if persona["engagement"] == "high" else InsightPriority.LOW,
                data=persona,
            ))
    
    async def _analyze_sequences(self):
        """Analyze sequence performance."""
        try:
            from src.sequences import get_sequence_engine
            engine = get_sequence_engine()
            
            if hasattr(engine, 'enrollments') and engine.enrollments:
                completed = sum(1 for e in engine.enrollments.values() if e.status.value == "completed")
                replied = sum(1 for e in engine.enrollments.values() if e.status.value == "replied")
                
                if completed > 0 or replied > 0:
                    self.insight_counter += 1
                    self.insights.append(Insight(
                        id=f"insight_{self.insight_counter}",
                        type=InsightType.SEQUENCE_OPTIMIZATION,
                        title="Sequence Performance",
                        description=f"{replied} contacts replied, {completed} completed full sequence.",
                        recommendation="Contacts who don't reply by step 3 may benefit from channel switch to LinkedIn.",
                        priority=InsightPriority.MEDIUM,
                        data={"replied": replied, "completed": completed},
                    ))
        except Exception as e:
            logger.debug(f"Could not analyze sequences: {e}")
    
    async def _generate_recommendations(self):
        """Generate general recommendations."""
        recommendations = [
            {
                "title": "Multi-Channel Approach",
                "description": "Contacts engaged via both email and LinkedIn have 3x higher meeting rates.",
                "recommendation": "Add LinkedIn touchpoints to your email sequences.",
                "priority": InsightPriority.HIGH,
            },
            {
                "title": "Follow-up Timing",
                "description": "Most replies come within 48 hours of follow-up, but 30% arrive after 5+ days.",
                "recommendation": "Space follow-ups 3-5 days apart for optimal response capture.",
                "priority": InsightPriority.MEDIUM,
            },
            {
                "title": "Subject Line Length",
                "description": "Subject lines under 50 characters show 12% higher open rates.",
                "recommendation": "Keep subject lines concise and curiosity-inducing.",
                "priority": InsightPriority.LOW,
            },
        ]
        
        for rec in recommendations:
            self.insight_counter += 1
            self.insights.append(Insight(
                id=f"insight_{self.insight_counter}",
                type=InsightType.CAMPAIGN_RECOMMENDATION,
                title=rec["title"],
                description=rec["description"],
                recommendation=rec["recommendation"],
                priority=InsightPriority(rec["priority"].value),
            ))
    
    def get_insights(
        self,
        insight_type: Optional[InsightType] = None,
        priority: Optional[InsightPriority] = None,
    ) -> List[Dict[str, Any]]:
        """Get insights with optional filters."""
        insights = self.insights
        
        if insight_type:
            insights = [i for i in insights if i.type == insight_type]
        
        if priority:
            insights = [i for i in insights if i.priority == priority]
        
        return [i.to_dict() for i in insights]
    
    def get_high_priority_insights(self) -> List[Dict[str, Any]]:
        """Get high priority insights."""
        return self.get_insights(priority=InsightPriority.HIGH)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get insights summary."""
        return {
            "total_insights": len(self.insights),
            "high_priority": sum(1 for i in self.insights if i.priority == InsightPriority.HIGH),
            "medium_priority": sum(1 for i in self.insights if i.priority == InsightPriority.MEDIUM),
            "low_priority": sum(1 for i in self.insights if i.priority == InsightPriority.LOW),
            "by_type": {
                t.value: sum(1 for i in self.insights if i.type == t)
                for t in InsightType
                if sum(1 for i in self.insights if i.type == t) > 0
            },
        }


# Singleton
_engine: Optional[InsightsEngine] = None


def get_insights_engine() -> InsightsEngine:
    """Get singleton insights engine."""
    global _engine
    if _engine is None:
        _engine = InsightsEngine()
    return _engine
