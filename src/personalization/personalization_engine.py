"""
Deep Personalization Engine
============================
Generates highly personalized content using company research,
contact behavior, industry trends, and historical engagement data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import structlog
import hashlib

logger = structlog.get_logger(__name__)


class InsightCategory(str, Enum):
    """Categories of personalization insights."""
    COMPANY_NEWS = "company_news"          # Recent company announcements
    FUNDING = "funding"                     # Funding rounds, investments
    HIRING = "hiring"                       # Job postings, team growth
    LEADERSHIP = "leadership"               # Leadership changes, promotions
    PRODUCT = "product"                     # Product launches, updates
    PARTNERSHIP = "partnership"             # Partnerships, acquisitions
    INDUSTRY = "industry"                   # Industry trends, news
    COMPETITOR = "competitor"               # Competitor activity
    SOCIAL = "social"                       # LinkedIn posts, tweets
    CONTENT = "content"                     # Blog posts, webinars, podcasts
    PAIN_POINT = "pain_point"              # Identified challenges
    TRIGGER_EVENT = "trigger_event"        # Events that signal buying intent
    SHARED_CONNECTION = "shared_connection" # Mutual connections, alma mater


@dataclass
class PersonalizationInsight:
    """A single personalization insight."""
    id: str
    category: InsightCategory
    title: str
    content: str
    source: str
    source_url: Optional[str] = None
    relevance_score: float = 0.5  # 0-1
    freshness_days: int = 0
    verified: bool = False
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "source_url": self.source_url,
            "relevance_score": self.relevance_score,
            "freshness_days": self.freshness_days,
            "verified": self.verified,
            "discovered_at": self.discovered_at.isoformat(),
        }


@dataclass
class PersonalizationContext:
    """Context for generating personalized content."""
    contact_id: str
    contact_name: str
    contact_email: str
    contact_title: str = ""
    company_id: Optional[str] = None
    company_name: str = ""
    company_domain: str = ""
    company_industry: str = ""
    company_size: str = ""
    persona: str = ""
    prior_engagement: list[dict] = field(default_factory=list)
    campaign_type: str = "cold_outreach"
    product_offering: str = ""
    value_prop: str = ""
    
    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "contact_title": self.contact_title,
            "company_id": self.company_id,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "company_industry": self.company_industry,
            "company_size": self.company_size,
            "persona": self.persona,
            "campaign_type": self.campaign_type,
        }


@dataclass
class PersonalizationResult:
    """Result of personalization generation."""
    contact_id: str
    insights: list[PersonalizationInsight] = field(default_factory=list)
    personalized_openers: list[str] = field(default_factory=list)
    personalized_hooks: list[str] = field(default_factory=list)
    personalized_ctas: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    talking_points: list[str] = field(default_factory=list)
    ice_breakers: list[str] = field(default_factory=list)
    personalization_score: float = 0.0  # 0-100
    generated_at: datetime = field(default_factory=datetime.utcnow)
    cache_key: str = ""
    
    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "insights": [i.to_dict() for i in self.insights],
            "personalized_openers": self.personalized_openers,
            "personalized_hooks": self.personalized_hooks,
            "personalized_ctas": self.personalized_ctas,
            "pain_points": self.pain_points,
            "talking_points": self.talking_points,
            "ice_breakers": self.ice_breakers,
            "personalization_score": self.personalization_score,
            "generated_at": self.generated_at.isoformat(),
        }


class PersonalizationEngine:
    """
    Generates deep personalization for sales outreach.
    Combines research data, engagement history, and AI to create
    highly relevant and personalized content.
    """
    
    def __init__(self):
        self.insight_cache: dict[str, list[PersonalizationInsight]] = {}
        self.result_cache: dict[str, PersonalizationResult] = {}
    
    async def generate_personalization(
        self,
        context: PersonalizationContext,
        max_insights: int = 5,
        force_refresh: bool = False,
    ) -> PersonalizationResult:
        """
        Generate personalization for a contact.
        
        Args:
            context: The personalization context
            max_insights: Maximum number of insights to include
            force_refresh: Whether to bypass cache
        
        Returns:
            PersonalizationResult with insights and personalized content
        """
        cache_key = self._generate_cache_key(context)
        
        # Check cache
        if not force_refresh and cache_key in self.result_cache:
            cached = self.result_cache[cache_key]
            # Cache is valid for 24 hours
            if (datetime.utcnow() - cached.generated_at).total_seconds() < 86400:
                return cached
        
        # Gather insights
        insights = await self._gather_insights(context, max_insights)
        
        # Generate personalized content
        openers = self._generate_openers(context, insights)
        hooks = self._generate_hooks(context, insights)
        ctas = self._generate_ctas(context, insights)
        pain_points = self._identify_pain_points(context, insights)
        talking_points = self._generate_talking_points(context, insights)
        ice_breakers = self._generate_ice_breakers(context, insights)
        
        # Calculate personalization score
        score = self._calculate_personalization_score(insights, openers, hooks)
        
        result = PersonalizationResult(
            contact_id=context.contact_id,
            insights=insights,
            personalized_openers=openers,
            personalized_hooks=hooks,
            personalized_ctas=ctas,
            pain_points=pain_points,
            talking_points=talking_points,
            ice_breakers=ice_breakers,
            personalization_score=score,
            cache_key=cache_key,
        )
        
        # Cache result
        self.result_cache[cache_key] = result
        
        logger.info(
            "personalization_generated",
            contact_id=context.contact_id,
            insights_count=len(insights),
            score=score,
        )
        
        return result
    
    async def _gather_insights(
        self,
        context: PersonalizationContext,
        max_insights: int,
    ) -> list[PersonalizationInsight]:
        """Gather personalization insights from various sources."""
        insights = []
        
        # Company news insights
        if context.company_name:
            company_insights = await self._get_company_insights(context)
            insights.extend(company_insights)
        
        # Industry insights
        if context.company_industry:
            industry_insights = await self._get_industry_insights(context)
            insights.extend(industry_insights)
        
        # Contact-specific insights
        contact_insights = await self._get_contact_insights(context)
        insights.extend(contact_insights)
        
        # Engagement-based insights
        if context.prior_engagement:
            engagement_insights = self._analyze_engagement(context)
            insights.extend(engagement_insights)
        
        # Sort by relevance and freshness
        insights.sort(
            key=lambda x: (x.relevance_score * 0.7 + (1 - x.freshness_days / 30) * 0.3),
            reverse=True
        )
        
        return insights[:max_insights]
    
    async def _get_company_insights(
        self,
        context: PersonalizationContext,
    ) -> list[PersonalizationInsight]:
        """Get company-related insights."""
        insights = []
        
        # Simulate fetching company news/data
        # In production, this would call Clearbit, ZoomInfo, news APIs, etc.
        
        # Sample company insights based on common patterns
        if context.company_size:
            if "1000" in context.company_size or "enterprise" in context.company_size.lower():
                insights.append(PersonalizationInsight(
                    id=f"company_scale_{context.company_id}",
                    category=InsightCategory.COMPANY_NEWS,
                    title="Enterprise Scale Operations",
                    content=f"{context.company_name} operates at enterprise scale with complex requirements",
                    source="company_analysis",
                    relevance_score=0.7,
                    freshness_days=0,
                ))
        
        # Growth indicators
        insights.append(PersonalizationInsight(
            id=f"growth_{context.company_id}",
            category=InsightCategory.HIRING,
            title="Active Hiring",
            content=f"{context.company_name} appears to be actively growing their team",
            source="job_board_analysis",
            relevance_score=0.6,
            freshness_days=7,
        ))
        
        return insights
    
    async def _get_industry_insights(
        self,
        context: PersonalizationContext,
    ) -> list[PersonalizationInsight]:
        """Get industry-related insights."""
        insights = []
        
        industry = context.company_industry.lower()
        
        # Industry-specific insights
        industry_trends = {
            "technology": [
                ("AI Integration", "Companies are rapidly adopting AI to improve efficiency"),
                ("Security Concerns", "Cybersecurity remains a top priority"),
            ],
            "finance": [
                ("Regulatory Compliance", "New regulations are driving technology adoption"),
                ("Digital Transformation", "Financial services digitizing customer experience"),
            ],
            "healthcare": [
                ("Telehealth Growth", "Remote healthcare delivery continues expanding"),
                ("Data Privacy", "HIPAA compliance driving technology decisions"),
            ],
            "retail": [
                ("E-commerce Shift", "Online channels becoming primary revenue source"),
                ("Supply Chain", "Supply chain optimization is critical"),
            ],
        }
        
        for ind_key, trends in industry_trends.items():
            if ind_key in industry:
                for title, content in trends:
                    insights.append(PersonalizationInsight(
                        id=f"industry_{ind_key}_{title}",
                        category=InsightCategory.INDUSTRY,
                        title=title,
                        content=content,
                        source="industry_research",
                        relevance_score=0.5,
                        freshness_days=14,
                    ))
        
        return insights
    
    async def _get_contact_insights(
        self,
        context: PersonalizationContext,
    ) -> list[PersonalizationInsight]:
        """Get contact-specific insights."""
        insights = []
        
        title = context.contact_title.lower()
        
        # Role-based pain points
        role_insights = {
            "ceo": ("Strategic Growth", "CEOs focused on scaling efficiently and market expansion"),
            "cto": ("Technical Excellence", "CTOs balancing innovation with reliability"),
            "cfo": ("Financial Optimization", "CFOs seeking ROI and cost efficiency"),
            "vp sales": ("Revenue Growth", "VP Sales focused on pipeline and team performance"),
            "marketing": ("Demand Generation", "Marketing teams driving qualified leads"),
            "operations": ("Process Efficiency", "Operations leaders optimizing workflows"),
        }
        
        for role_key, (title_text, content) in role_insights.items():
            if role_key in title:
                insights.append(PersonalizationInsight(
                    id=f"role_{context.contact_id}_{role_key}",
                    category=InsightCategory.PAIN_POINT,
                    title=title_text,
                    content=content,
                    source="role_analysis",
                    relevance_score=0.8,
                    freshness_days=0,
                ))
        
        return insights
    
    def _analyze_engagement(
        self,
        context: PersonalizationContext,
    ) -> list[PersonalizationInsight]:
        """Analyze prior engagement for insights."""
        insights = []
        
        for engagement in context.prior_engagement:
            eng_type = engagement.get("type", "")
            
            if eng_type == "email_opened":
                insights.append(PersonalizationInsight(
                    id=f"engagement_{engagement.get('id', '')}",
                    category=InsightCategory.TRIGGER_EVENT,
                    title="Email Engagement",
                    content="Contact has opened previous emails, showing interest",
                    source="engagement_tracking",
                    relevance_score=0.7,
                    freshness_days=engagement.get("days_ago", 0),
                ))
            elif eng_type == "content_download":
                insights.append(PersonalizationInsight(
                    id=f"content_{engagement.get('id', '')}",
                    category=InsightCategory.CONTENT,
                    title="Content Interest",
                    content=f"Downloaded: {engagement.get('content_name', 'resource')}",
                    source="content_tracking",
                    relevance_score=0.8,
                    freshness_days=engagement.get("days_ago", 0),
                ))
        
        return insights
    
    def _generate_openers(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Generate personalized email openers."""
        openers = []
        
        # Company-based opener
        if context.company_name:
            openers.append(
                f"I noticed {context.company_name} is making moves in {context.company_industry or 'your industry'} - "
                f"that caught my attention."
            )
        
        # Role-based opener
        if context.contact_title:
            openers.append(
                f"As {context.contact_title}, I imagine you're focused on driving results "
                f"while navigating the challenges of scaling."
            )
        
        # Insight-based openers
        for insight in insights[:2]:
            if insight.category == InsightCategory.COMPANY_NEWS:
                openers.append(
                    f"I saw the news about {insight.title.lower()} at {context.company_name} - "
                    f"impressive progress."
                )
            elif insight.category == InsightCategory.HIRING:
                openers.append(
                    f"I noticed {context.company_name} is growing the team - "
                    f"exciting times ahead."
                )
        
        return openers[:3]
    
    def _generate_hooks(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Generate personalized value hooks."""
        hooks = []
        
        # Industry-specific hooks
        industry = context.company_industry.lower() if context.company_industry else ""
        
        if "tech" in industry:
            hooks.append(
                "We've helped similar tech companies reduce sales cycle time by 40% "
                "while increasing pipeline velocity."
            )
        elif "finance" in industry:
            hooks.append(
                "Financial services teams using our platform see 3x improvement in "
                "prospect engagement while maintaining compliance."
            )
        else:
            hooks.append(
                "Companies like yours have seen significant improvements in outreach "
                "efficiency and conversion rates."
            )
        
        # Size-based hooks
        if context.company_size and "enterprise" in context.company_size.lower():
            hooks.append(
                "Our enterprise clients appreciate the scalability and security "
                "that comes built-in."
            )
        
        # Pain point hooks
        for insight in insights:
            if insight.category == InsightCategory.PAIN_POINT:
                hooks.append(
                    f"Given your focus on {insight.title.lower()}, I think you'd find "
                    f"our approach particularly valuable."
                )
        
        return hooks[:3]
    
    def _generate_ctas(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Generate personalized calls-to-action."""
        ctas = []
        
        # Standard CTAs with personalization
        ctas.append(
            f"Would you have 15 minutes this week to explore how we could help "
            f"{context.company_name or 'your team'}?"
        )
        
        ctas.append(
            "I'd love to show you a quick demo tailored to your specific use case - "
            "would that be helpful?"
        )
        
        # Role-specific CTAs
        title = context.contact_title.lower()
        if "exec" in title or "chief" in title or "vp" in title:
            ctas.append(
                "Happy to send over a brief executive summary if that would be "
                "more efficient for your schedule."
            )
        else:
            ctas.append(
                "Would you prefer a hands-on demo or a quick call to discuss your needs?"
            )
        
        return ctas[:3]
    
    def _identify_pain_points(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Identify potential pain points."""
        pain_points = []
        
        # From insights
        for insight in insights:
            if insight.category == InsightCategory.PAIN_POINT:
                pain_points.append(insight.content)
        
        # Role-based pain points
        title = context.contact_title.lower()
        
        if "sales" in title:
            pain_points.extend([
                "Manual prospecting taking too much time",
                "Inconsistent outreach quality across the team",
                "Difficulty scaling personalized outreach",
            ])
        elif "marketing" in title:
            pain_points.extend([
                "Lead quality and marketing-sales alignment",
                "Measuring true ROI of campaigns",
                "Personalizing at scale",
            ])
        elif "ceo" in title or "founder" in title:
            pain_points.extend([
                "Scaling revenue efficiently",
                "Team productivity and performance",
                "Strategic growth initiatives",
            ])
        
        return list(set(pain_points))[:5]
    
    def _generate_talking_points(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Generate talking points for calls/meetings."""
        points = []
        
        points.append(f"Discuss {context.company_name}'s current sales/outreach process")
        points.append("Explore biggest challenges with prospect engagement")
        points.append("Share relevant case studies from similar companies")
        
        for insight in insights[:2]:
            points.append(f"Connect {insight.title} to our value proposition")
        
        points.append("Propose next steps and pilot program")
        
        return points
    
    def _generate_ice_breakers(
        self,
        context: PersonalizationContext,
        insights: list[PersonalizationInsight],
    ) -> list[str]:
        """Generate conversation ice breakers."""
        ice_breakers = []
        
        if context.company_name:
            ice_breakers.append(
                f"How long have you been with {context.company_name}?"
            )
        
        if context.company_industry:
            ice_breakers.append(
                f"What trends are you seeing in the {context.company_industry} space?"
            )
        
        for insight in insights:
            if insight.category == InsightCategory.COMPANY_NEWS:
                ice_breakers.append(
                    f"I saw the news about {insight.title} - how has that been going?"
                )
        
        ice_breakers.append("What's keeping you busiest this quarter?")
        
        return ice_breakers[:3]
    
    def _calculate_personalization_score(
        self,
        insights: list[PersonalizationInsight],
        openers: list[str],
        hooks: list[str],
    ) -> float:
        """Calculate overall personalization score (0-100)."""
        score = 0.0
        
        # Insights contribute 40%
        insight_score = min(40, len(insights) * 8)
        avg_relevance = sum(i.relevance_score for i in insights) / len(insights) if insights else 0
        insight_score *= avg_relevance
        score += insight_score
        
        # Openers contribute 20%
        opener_score = min(20, len(openers) * 7)
        score += opener_score
        
        # Hooks contribute 20%
        hook_score = min(20, len(hooks) * 7)
        score += hook_score
        
        # Base score for having context
        score += 20
        
        return min(100, score)
    
    def _generate_cache_key(self, context: PersonalizationContext) -> str:
        """Generate a cache key for the context."""
        key_data = f"{context.contact_id}:{context.company_id}:{context.campaign_type}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def clear_cache(self, contact_id: str = None) -> int:
        """Clear cached results."""
        if contact_id:
            keys_to_remove = [k for k, v in self.result_cache.items() if v.contact_id == contact_id]
            for key in keys_to_remove:
                del self.result_cache[key]
            return len(keys_to_remove)
        else:
            count = len(self.result_cache)
            self.result_cache.clear()
            return count


# Singleton instance
_engine: Optional[PersonalizationEngine] = None


def get_personalization_engine() -> PersonalizationEngine:
    """Get the personalization engine singleton."""
    global _engine
    if _engine is None:
        _engine = PersonalizationEngine()
    return _engine
