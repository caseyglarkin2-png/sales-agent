"""
Competitor Service - Competitive Intelligence
==============================================
Manages competitor tracking and battle cards.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class CompetitorStatus(str, Enum):
    """Competitor status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EMERGING = "emerging"
    DECLINING = "declining"


class ThreatLevel(str, Enum):
    """Competitor threat level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MentionSource(str, Enum):
    """Where competitor was mentioned."""
    DEAL = "deal"
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    WEBSITE = "website"
    NEWS = "news"
    SOCIAL = "social"
    MANUAL = "manual"


class MentionOutcome(str, Enum):
    """Outcome when competitor was mentioned."""
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    NO_DECISION = "no_decision"


@dataclass
class CompetitorStrength:
    """A competitor strength or weakness."""
    id: str
    category: str  # pricing, features, support, etc.
    description: str
    is_strength: bool  # True = strength, False = weakness
    impact_score: int = 5  # 1-10
    evidence: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BattleCard:
    """A battle card for competitive selling."""
    id: str
    competitor_id: str
    title: str
    
    # Quick overview
    overview: str = ""
    positioning: str = ""
    target_market: str = ""
    
    # Strengths and weaknesses
    strengths: list[CompetitorStrength] = field(default_factory=list)
    weaknesses: list[CompetitorStrength] = field(default_factory=list)
    
    # Sales tactics
    discovery_questions: list[str] = field(default_factory=list)
    objection_handlers: dict[str, str] = field(default_factory=dict)
    talking_points: list[str] = field(default_factory=list)
    traps: list[str] = field(default_factory=list)  # Things to avoid
    
    # Differentiation
    differentiators: list[str] = field(default_factory=list)
    feature_comparison: dict[str, dict[str, Any]] = field(default_factory=dict)
    
    # Resources
    case_studies: list[str] = field(default_factory=list)
    collateral_links: list[str] = field(default_factory=list)
    
    # Status
    is_published: bool = False
    last_reviewed: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompetitorMention:
    """A mention of a competitor in a deal or activity."""
    id: str
    competitor_id: str
    source: MentionSource
    source_id: Optional[str]  # Deal ID, call ID, etc.
    
    # Context
    context: str = ""
    deal_amount: Optional[float] = None
    
    # Outcome
    outcome: MentionOutcome = MentionOutcome.PENDING
    won_reason: Optional[str] = None
    lost_reason: Optional[str] = None
    
    # Metadata
    mentioned_by: Optional[str] = None
    mentioned_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Competitor:
    """A competitor."""
    id: str
    name: str
    website: str
    description: str
    
    # Classification
    status: CompetitorStatus = CompetitorStatus.ACTIVE
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    
    # Company info
    logo_url: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    employee_count: Optional[str] = None  # "51-200", etc.
    funding: Optional[str] = None
    revenue_estimate: Optional[str] = None
    
    # Products
    products: list[str] = field(default_factory=list)
    pricing_model: Optional[str] = None
    price_range: Optional[str] = None
    
    # Positioning
    target_market: str = ""
    value_proposition: str = ""
    key_features: list[str] = field(default_factory=list)
    
    # Strengths and weaknesses
    strengths: list[CompetitorStrength] = field(default_factory=list)
    weaknesses: list[CompetitorStrength] = field(default_factory=list)
    
    # Tracking
    mentions: list[CompetitorMention] = field(default_factory=list)
    battle_cards: list[str] = field(default_factory=list)  # Battle card IDs
    
    # Win/loss stats
    total_encounters: int = 0
    wins_against: int = 0
    losses_to: int = 0
    
    # Tags and notes
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate against this competitor."""
        total = self.wins_against + self.losses_to
        if total == 0:
            return 0.0
        return (self.wins_against / total) * 100


class CompetitorService:
    """Service for competitor management."""
    
    def __init__(self):
        self.competitors: dict[str, Competitor] = {}
        self.battle_cards: dict[str, BattleCard] = {}
        self.mentions: dict[str, CompetitorMention] = {}
    
    # Competitor CRUD
    async def create_competitor(
        self,
        name: str,
        website: str,
        description: str,
        **kwargs
    ) -> Competitor:
        """Create a new competitor."""
        competitor_id = str(uuid.uuid4())
        
        competitor = Competitor(
            id=competitor_id,
            name=name,
            website=website,
            description=description,
            **kwargs
        )
        
        self.competitors[competitor_id] = competitor
        return competitor
    
    async def get_competitor(self, competitor_id: str) -> Optional[Competitor]:
        """Get a competitor by ID."""
        return self.competitors.get(competitor_id)
    
    async def get_by_name(self, name: str) -> Optional[Competitor]:
        """Get competitor by name."""
        name_lower = name.lower()
        for competitor in self.competitors.values():
            if competitor.name.lower() == name_lower:
                return competitor
        return None
    
    async def update_competitor(
        self,
        competitor_id: str,
        updates: dict[str, Any]
    ) -> Optional[Competitor]:
        """Update a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        for key, value in updates.items():
            if hasattr(competitor, key):
                setattr(competitor, key, value)
        
        competitor.updated_at = datetime.utcnow()
        return competitor
    
    async def delete_competitor(self, competitor_id: str) -> bool:
        """Delete a competitor."""
        if competitor_id in self.competitors:
            del self.competitors[competitor_id]
            return True
        return False
    
    async def list_competitors(
        self,
        status: Optional[CompetitorStatus] = None,
        threat_level: Optional[ThreatLevel] = None,
        search: Optional[str] = None
    ) -> list[Competitor]:
        """List competitors with filters."""
        competitors = list(self.competitors.values())
        
        if status:
            competitors = [c for c in competitors if c.status == status]
        if threat_level:
            competitors = [c for c in competitors if c.threat_level == threat_level]
        if search:
            search_lower = search.lower()
            competitors = [
                c for c in competitors
                if search_lower in c.name.lower() or search_lower in c.description.lower()
            ]
        
        competitors.sort(key=lambda c: c.name)
        return competitors
    
    # Strengths and weaknesses
    async def add_strength(
        self,
        competitor_id: str,
        category: str,
        description: str,
        impact_score: int = 5,
        evidence: str = ""
    ) -> Optional[CompetitorStrength]:
        """Add a strength to a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        strength = CompetitorStrength(
            id=str(uuid.uuid4()),
            category=category,
            description=description,
            is_strength=True,
            impact_score=impact_score,
            evidence=evidence,
        )
        
        competitor.strengths.append(strength)
        competitor.updated_at = datetime.utcnow()
        
        return strength
    
    async def add_weakness(
        self,
        competitor_id: str,
        category: str,
        description: str,
        impact_score: int = 5,
        evidence: str = ""
    ) -> Optional[CompetitorStrength]:
        """Add a weakness to a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        weakness = CompetitorStrength(
            id=str(uuid.uuid4()),
            category=category,
            description=description,
            is_strength=False,
            impact_score=impact_score,
            evidence=evidence,
        )
        
        competitor.weaknesses.append(weakness)
        competitor.updated_at = datetime.utcnow()
        
        return weakness
    
    async def remove_strength_or_weakness(
        self,
        competitor_id: str,
        item_id: str
    ) -> bool:
        """Remove a strength or weakness."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return False
        
        original_s = len(competitor.strengths)
        original_w = len(competitor.weaknesses)
        
        competitor.strengths = [s for s in competitor.strengths if s.id != item_id]
        competitor.weaknesses = [w for w in competitor.weaknesses if w.id != item_id]
        
        if len(competitor.strengths) < original_s or len(competitor.weaknesses) < original_w:
            competitor.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Mentions
    async def record_mention(
        self,
        competitor_id: str,
        source: MentionSource,
        context: str = "",
        source_id: Optional[str] = None,
        deal_amount: Optional[float] = None,
        mentioned_by: Optional[str] = None
    ) -> Optional[CompetitorMention]:
        """Record a competitor mention."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        mention = CompetitorMention(
            id=str(uuid.uuid4()),
            competitor_id=competitor_id,
            source=source,
            source_id=source_id,
            context=context,
            deal_amount=deal_amount,
            mentioned_by=mentioned_by,
        )
        
        competitor.mentions.append(mention)
        competitor.total_encounters += 1
        competitor.updated_at = datetime.utcnow()
        
        self.mentions[mention.id] = mention
        
        return mention
    
    async def update_mention_outcome(
        self,
        mention_id: str,
        outcome: MentionOutcome,
        reason: Optional[str] = None
    ) -> Optional[CompetitorMention]:
        """Update the outcome of a mention."""
        mention = self.mentions.get(mention_id)
        if not mention:
            return None
        
        old_outcome = mention.outcome
        mention.outcome = outcome
        
        if outcome == MentionOutcome.WON:
            mention.won_reason = reason
        elif outcome == MentionOutcome.LOST:
            mention.lost_reason = reason
        
        # Update win/loss stats
        competitor = self.competitors.get(mention.competitor_id)
        if competitor:
            # Remove old outcome
            if old_outcome == MentionOutcome.WON:
                competitor.wins_against -= 1
            elif old_outcome == MentionOutcome.LOST:
                competitor.losses_to -= 1
            
            # Add new outcome
            if outcome == MentionOutcome.WON:
                competitor.wins_against += 1
            elif outcome == MentionOutcome.LOST:
                competitor.losses_to += 1
            
            competitor.updated_at = datetime.utcnow()
        
        return mention
    
    async def get_mentions(
        self,
        competitor_id: str,
        source: Optional[MentionSource] = None,
        outcome: Optional[MentionOutcome] = None,
        limit: int = 50
    ) -> list[CompetitorMention]:
        """Get mentions for a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return []
        
        mentions = competitor.mentions.copy()
        
        if source:
            mentions = [m for m in mentions if m.source == source]
        if outcome:
            mentions = [m for m in mentions if m.outcome == outcome]
        
        mentions.sort(key=lambda m: m.mentioned_at, reverse=True)
        
        return mentions[:limit]
    
    # Battle cards
    async def create_battle_card(
        self,
        competitor_id: str,
        title: str,
        **kwargs
    ) -> Optional[BattleCard]:
        """Create a battle card."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        battle_card = BattleCard(
            id=str(uuid.uuid4()),
            competitor_id=competitor_id,
            title=title,
            **kwargs
        )
        
        self.battle_cards[battle_card.id] = battle_card
        competitor.battle_cards.append(battle_card.id)
        competitor.updated_at = datetime.utcnow()
        
        return battle_card
    
    async def get_battle_card(self, battle_card_id: str) -> Optional[BattleCard]:
        """Get a battle card by ID."""
        return self.battle_cards.get(battle_card_id)
    
    async def update_battle_card(
        self,
        battle_card_id: str,
        updates: dict[str, Any]
    ) -> Optional[BattleCard]:
        """Update a battle card."""
        battle_card = self.battle_cards.get(battle_card_id)
        if not battle_card:
            return None
        
        for key, value in updates.items():
            if hasattr(battle_card, key):
                setattr(battle_card, key, value)
        
        battle_card.updated_at = datetime.utcnow()
        return battle_card
    
    async def publish_battle_card(
        self,
        battle_card_id: str,
        reviewer_id: str
    ) -> bool:
        """Publish a battle card."""
        battle_card = self.battle_cards.get(battle_card_id)
        if not battle_card:
            return False
        
        battle_card.is_published = True
        battle_card.last_reviewed = datetime.utcnow()
        battle_card.reviewed_by = reviewer_id
        battle_card.updated_at = datetime.utcnow()
        
        return True
    
    async def list_battle_cards(
        self,
        competitor_id: Optional[str] = None,
        published_only: bool = False
    ) -> list[BattleCard]:
        """List battle cards."""
        cards = list(self.battle_cards.values())
        
        if competitor_id:
            cards = [c for c in cards if c.competitor_id == competitor_id]
        if published_only:
            cards = [c for c in cards if c.is_published]
        
        cards.sort(key=lambda c: c.title)
        return cards
    
    async def add_objection_handler(
        self,
        battle_card_id: str,
        objection: str,
        response: str
    ) -> bool:
        """Add an objection handler to a battle card."""
        battle_card = self.battle_cards.get(battle_card_id)
        if not battle_card:
            return False
        
        battle_card.objection_handlers[objection] = response
        battle_card.updated_at = datetime.utcnow()
        
        return True
    
    async def add_discovery_question(
        self,
        battle_card_id: str,
        question: str
    ) -> bool:
        """Add a discovery question to a battle card."""
        battle_card = self.battle_cards.get(battle_card_id)
        if not battle_card:
            return False
        
        if question not in battle_card.discovery_questions:
            battle_card.discovery_questions.append(question)
            battle_card.updated_at = datetime.utcnow()
        
        return True
    
    # Analytics
    async def get_competitor_stats(
        self,
        competitor_id: str
    ) -> Optional[dict[str, Any]]:
        """Get statistics for a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return None
        
        mentions = competitor.mentions
        
        # By source
        by_source = {}
        for mention in mentions:
            source = mention.source.value
            by_source[source] = by_source.get(source, 0) + 1
        
        # By outcome
        by_outcome = {}
        for mention in mentions:
            outcome = mention.outcome.value
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        
        # Deal value
        won_deals = [m for m in mentions if m.outcome == MentionOutcome.WON and m.deal_amount]
        lost_deals = [m for m in mentions if m.outcome == MentionOutcome.LOST and m.deal_amount]
        
        return {
            "competitor_id": competitor.id,
            "name": competitor.name,
            "threat_level": competitor.threat_level.value,
            "total_encounters": competitor.total_encounters,
            "wins_against": competitor.wins_against,
            "losses_to": competitor.losses_to,
            "win_rate": competitor.win_rate,
            "by_source": by_source,
            "by_outcome": by_outcome,
            "total_won_value": sum(m.deal_amount for m in won_deals),
            "total_lost_value": sum(m.deal_amount for m in lost_deals),
            "avg_won_deal": sum(m.deal_amount for m in won_deals) / len(won_deals) if won_deals else 0,
            "strength_count": len(competitor.strengths),
            "weakness_count": len(competitor.weaknesses),
            "battle_card_count": len(competitor.battle_cards),
        }
    
    async def get_win_loss_analysis(self) -> dict[str, Any]:
        """Get overall win/loss analysis against all competitors."""
        results = []
        
        for competitor in self.competitors.values():
            results.append({
                "competitor_id": competitor.id,
                "name": competitor.name,
                "threat_level": competitor.threat_level.value,
                "encounters": competitor.total_encounters,
                "wins": competitor.wins_against,
                "losses": competitor.losses_to,
                "win_rate": competitor.win_rate,
            })
        
        # Sort by encounters
        results.sort(key=lambda x: x["encounters"], reverse=True)
        
        total_encounters = sum(r["encounters"] for r in results)
        total_wins = sum(r["wins"] for r in results)
        total_losses = sum(r["losses"] for r in results)
        
        return {
            "competitors": results,
            "totals": {
                "total_encounters": total_encounters,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "overall_win_rate": (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0,
            }
        }
    
    async def get_top_reasons(
        self,
        competitor_id: str,
        outcome: MentionOutcome,
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """Get top win/loss reasons against a competitor."""
        competitor = self.competitors.get(competitor_id)
        if not competitor:
            return []
        
        reasons = {}
        for mention in competitor.mentions:
            if mention.outcome != outcome:
                continue
            
            reason = mention.won_reason if outcome == MentionOutcome.WON else mention.lost_reason
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
        
        # Sort by count
        sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"reason": reason, "count": count}
            for reason, count in sorted_reasons[:limit]
        ]


# Singleton instance
_competitor_service: Optional[CompetitorService] = None


def get_competitor_service() -> CompetitorService:
    """Get competitor service singleton."""
    global _competitor_service
    if _competitor_service is None:
        _competitor_service = CompetitorService()
    return _competitor_service
