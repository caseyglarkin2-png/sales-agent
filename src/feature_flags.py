"""Feature flag management."""
from typing import Any, Dict

from src.logger import get_logger

logger = get_logger(__name__)


class FeatureFlagManager:
    """Centralized feature flag management."""

    def __init__(self, flags: Dict[str, bool]):
        """Initialize feature flag manager."""
        self.flags = flags
        logger.info(f"Feature flags initialized: {flags}")

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled."""
        enabled = self.flags.get(flag_name, False)
        logger.debug(f"Feature flag '{flag_name}' is {'enabled' if enabled else 'disabled'}")
        return enabled

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Set a feature flag."""
        self.flags[flag_name] = enabled
        logger.info(f"Set feature flag '{flag_name}' to {enabled}")

    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return self.flags.copy()
