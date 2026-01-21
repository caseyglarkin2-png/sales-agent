"""
Gamification Module
===================
Gamification features for sales team engagement and motivation.
"""

from .gamification_service import (
    GamificationService,
    Badge,
    Achievement,
    Leaderboard,
    Challenge,
    Reward,
    UserProgress,
    get_gamification_service,
)

__all__ = [
    "GamificationService",
    "Badge",
    "Achievement",
    "Leaderboard",
    "Challenge",
    "Reward",
    "UserProgress",
    "get_gamification_service",
]
