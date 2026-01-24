"""CompetitorWatchAgent - Monitor competitors and market intelligence.

Tracks competitor activities, pricing changes, and market movements.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class SignalType(str, Enum):
    """Types of competitive signals."""
    PRICING_CHANGE = "pricing_change"
    NEW_PRODUCT = "new_product"
    FEATURE_LAUNCH = "feature_launch"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    LEADERSHIP_CHANGE = "leadership_change"
    FUNDING = "funding"
    CUSTOMER_WIN = "customer_win"
    CUSTOMER_LOSS = "customer_loss"
    MARKETING_CAMPAIGN = "marketing_campaign"
    CONTENT_PUBLISH = "content_publish"


class CompetitorWatchAgent(BaseAgent):
    """Monitors competitors and surfaces relevant intelligence.
    
    Features:
    - Competitor profile management
    - Signal tracking and alerting
    - Competitive positioning analysis
    - Battle card generation
    - Win/loss tracking
    
    Example:
        agent = CompetitorWatchAgent()
        result = await agent.execute({
            "action": "track_signal",
            "competitor": "CompetitorX",
            "signal_type": "pricing_change",
            "details": "Lowered enterprise pricing by 20%",
        })
    """

    def __init__(self, llm_connector=None):
        """Initialize competitor watch agent."""
        super().__init__(
            name="Competitor Watch Agent",
            description="Monitors competitors and surfaces market intelligence"
        )
        self.llm_connector = llm_connector
        
        # In-memory storage (would be DB in production)
        self._competitors: Dict[str, Dict[str, Any]] = {}
        self._signals: List[Dict[str, Any]] = []
        self._battle_cards: Dict[str, Dict[str, Any]] = {}

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "list")
        if action == "track_signal":
            return "competitor" in context and "signal_type" in context
        elif action == "add_competitor":
            return "name" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute competitor watch action."""
        action = context.get("action", "list")
        
        if action == "add_competitor":
            return await self._add_competitor(context)
        elif action == "track_signal":
            return await self._track_signal(context)
        elif action == "list_competitors":
            return await self._list_competitors(context)
        elif action == "list_signals":
            return await self._list_signals(context)
        elif action == "get_battle_card":
            return await self._get_battle_card(context)
        elif action == "compare":
            return await self._compare_competitors(context)
        elif action == "win_loss":
            return await self._track_win_loss(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _add_competitor(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new competitor to track."""
        competitor_id = context["name"].lower().replace(" ", "_")
        
        competitor = {
            "id": competitor_id,
            "name": context["name"],
            "website": context.get("website"),
            "description": context.get("description"),
            "category": context.get("category", "direct"),  # direct, indirect, emerging
            "strengths": context.get("strengths", []),
            "weaknesses": context.get("weaknesses", []),
            "pricing": context.get("pricing"),
            "target_market": context.get("target_market"),
            "key_customers": context.get("key_customers", []),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        self._competitors[competitor_id] = competitor
        
        logger.info(f"Added competitor: {competitor['name']}")
        
        return {
            "status": "success",
            "competitor": competitor,
        }

    async def _track_signal(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Track a competitive signal/event."""
        signal_id = f"sig-{datetime.utcnow().timestamp()}"
        
        signal = {
            "id": signal_id,
            "competitor": context["competitor"],
            "signal_type": context["signal_type"],
            "details": context.get("details", ""),
            "source": context.get("source", "manual"),
            "source_url": context.get("source_url"),
            "impact": context.get("impact", "medium"),  # low, medium, high
            "action_required": context.get("action_required", False),
            "tracked_at": datetime.utcnow().isoformat(),
        }
        
        self._signals.append(signal)
        
        # Update competitor last activity
        competitor_id = context["competitor"].lower().replace(" ", "_")
        if competitor_id in self._competitors:
            self._competitors[competitor_id]["last_activity"] = signal["tracked_at"]
            self._competitors[competitor_id]["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Tracked signal: {signal['signal_type']} for {signal['competitor']}")
        
        # Generate alert if high impact
        alert = None
        if signal["impact"] == "high" or signal["action_required"]:
            alert = {
                "message": f"⚠️ High-impact competitive signal: {signal['competitor']} - {signal['signal_type']}",
                "details": signal["details"],
                "suggested_action": self._suggest_response(signal),
            }
        
        return {
            "status": "success",
            "signal": signal,
            "alert": alert,
        }

    async def _list_competitors(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List tracked competitors."""
        category = context.get("category")
        
        competitors = list(self._competitors.values())
        
        if category:
            competitors = [c for c in competitors if c.get("category") == category]
        
        return {
            "status": "success",
            "count": len(competitors),
            "competitors": competitors,
        }

    async def _list_signals(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List recent competitive signals."""
        competitor = context.get("competitor")
        signal_type = context.get("signal_type")
        days = context.get("days", 30)
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        signals = self._signals
        
        # Filter
        signals = [
            s for s in signals 
            if datetime.fromisoformat(s["tracked_at"].replace("Z", "+00:00")) > cutoff
        ]
        
        if competitor:
            signals = [s for s in signals if s["competitor"].lower() == competitor.lower()]
        if signal_type:
            signals = [s for s in signals if s["signal_type"] == signal_type]
        
        # Sort by recency
        signals = sorted(signals, key=lambda x: x["tracked_at"], reverse=True)
        
        return {
            "status": "success",
            "count": len(signals),
            "signals": signals,
        }

    async def _get_battle_card(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get or generate a battle card for a competitor."""
        competitor_name = context.get("competitor")
        competitor_id = competitor_name.lower().replace(" ", "_")
        
        if competitor_id not in self._competitors:
            return {"status": "error", "error": f"Competitor not found: {competitor_name}"}
        
        competitor = self._competitors[competitor_id]
        
        # Get recent signals
        recent_signals = [
            s for s in self._signals 
            if s["competitor"].lower() == competitor_name.lower()
        ][-5:]
        
        battle_card = {
            "competitor": competitor["name"],
            "overview": competitor.get("description", ""),
            "category": competitor.get("category", "direct"),
            
            "positioning": {
                "their_pitch": self._get_their_pitch(competitor),
                "our_response": self._get_our_response(competitor),
            },
            
            "strengths": competitor.get("strengths", []),
            "weaknesses": competitor.get("weaknesses", []),
            
            "pricing_comparison": {
                "their_pricing": competitor.get("pricing"),
                "our_advantage": "Value-based pricing with ROI focus",
            },
            
            "common_objections": self._get_common_objections(competitor),
            "win_themes": self._get_win_themes(competitor),
            "landmines": self._get_landmines(competitor),
            
            "recent_activity": recent_signals,
            
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        self._battle_cards[competitor_id] = battle_card
        
        return {
            "status": "success",
            "battle_card": battle_card,
        }

    async def _compare_competitors(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple competitors."""
        competitor_names = context.get("competitors", [])
        
        if len(competitor_names) < 2:
            return {"status": "error", "error": "Need at least 2 competitors to compare"}
        
        comparison = {
            "competitors": [],
            "criteria": [],
        }
        
        criteria = ["pricing", "target_market", "strengths", "weaknesses", "category"]
        comparison["criteria"] = criteria
        
        for name in competitor_names:
            competitor_id = name.lower().replace(" ", "_")
            if competitor_id in self._competitors:
                comp = self._competitors[competitor_id]
                comparison["competitors"].append({
                    "name": comp["name"],
                    "pricing": comp.get("pricing", "Unknown"),
                    "target_market": comp.get("target_market", "Unknown"),
                    "strengths": comp.get("strengths", []),
                    "weaknesses": comp.get("weaknesses", []),
                    "category": comp.get("category", "Unknown"),
                })
        
        return {
            "status": "success",
            "comparison": comparison,
        }

    async def _track_win_loss(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Track a competitive win or loss."""
        record = {
            "id": f"wl-{datetime.utcnow().timestamp()}",
            "outcome": context.get("outcome", "win"),  # win, loss
            "competitor": context.get("competitor"),
            "deal_name": context.get("deal_name"),
            "deal_value": context.get("deal_value"),
            "reasons": context.get("reasons", []),
            "learnings": context.get("learnings", ""),
            "recorded_at": datetime.utcnow().isoformat(),
        }
        
        # Track as a signal
        await self._track_signal({
            "competitor": context.get("competitor", "Unknown"),
            "signal_type": SignalType.CUSTOMER_WIN.value if record["outcome"] == "loss" else SignalType.CUSTOMER_LOSS.value,
            "details": f"{'Lost to' if record['outcome'] == 'loss' else 'Won against'} {context.get('competitor')}: {context.get('reasons', [])}",
            "impact": "high" if context.get("deal_value", 0) > 20000 else "medium",
        })
        
        logger.info(f"Recorded {record['outcome']}: {record['deal_name']} vs {record['competitor']}")
        
        return {
            "status": "success",
            "record": record,
        }

    def _suggest_response(self, signal: Dict[str, Any]) -> str:
        """Suggest a response action for a competitive signal."""
        signal_type = signal.get("signal_type")
        
        responses = {
            SignalType.PRICING_CHANGE.value: "Review our pricing positioning and prepare value comparison",
            SignalType.NEW_PRODUCT.value: "Analyze feature gaps and prepare differentiation messaging",
            SignalType.CUSTOMER_WIN.value: "Reach out to lost prospect for feedback; update battle card",
            SignalType.PARTNERSHIP.value: "Assess partnership impact and identify counter-opportunities",
            SignalType.MARKETING_CAMPAIGN.value: "Monitor campaign messaging and consider response",
        }
        
        return responses.get(signal_type, "Monitor situation and assess impact")

    def _get_their_pitch(self, competitor: Dict[str, Any]) -> str:
        """Get competitor's typical sales pitch."""
        return competitor.get("pitch", "Not yet documented - update competitor profile")

    def _get_our_response(self, competitor: Dict[str, Any]) -> str:
        """Get our counter-positioning."""
        weaknesses = competitor.get("weaknesses", [])
        if weaknesses:
            return f"Focus on: {', '.join(weaknesses[:2])}"
        return "Emphasize our unique value proposition and customer success track record"

    def _get_common_objections(self, competitor: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get common objections when competing."""
        return [
            {
                "objection": f"{competitor['name']} is cheaper",
                "response": "Let's look at total value delivered. Our clients see 3x ROI within 90 days.",
            },
            {
                "objection": f"{competitor['name']} has more features",
                "response": "Features don't equal outcomes. Let me show you what actually drives results.",
            },
        ]

    def _get_win_themes(self, competitor: Dict[str, Any]) -> List[str]:
        """Get themes that help us win against this competitor."""
        return [
            "Deep industry expertise",
            "Hands-on partnership model",
            "Measurable outcomes focus",
            "Speed to value",
        ]

    def _get_landmines(self, competitor: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get topics to avoid or handle carefully."""
        return [
            {
                "topic": "Enterprise scale",
                "risk": f"{competitor['name']} may have more enterprise references",
                "mitigation": "Focus on agility and outcomes over scale",
            },
        ]
