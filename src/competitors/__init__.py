"""
Competitors Module - Competitive Intelligence
==============================================
Track and manage competitor information.
"""

from .competitor_service import (
    CompetitorService,
    Competitor,
    CompetitorMention,
    BattleCard,
    get_competitor_service,
)

__all__ = [
    "CompetitorService",
    "Competitor",
    "CompetitorMention",
    "BattleCard",
    "get_competitor_service",
]
