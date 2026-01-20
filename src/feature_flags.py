"""Feature flag management."""
import os
from enum import Enum
from typing import Any, Dict

from src.logger import get_logger

logger = get_logger(__name__)


class WorkflowMode(Enum):
    """Workflow execution mode."""
    DRAFT_ONLY = "draft_only"  # Create drafts, do not send
    SEND = "send"  # Create and send (requires explicit enable)


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

    @staticmethod
    def get_workflow_mode() -> WorkflowMode:
        """Get current workflow mode from environment."""
        mode = os.environ.get("WORKFLOW_MODE", "draft_only").lower()
        if mode == "send":
            return WorkflowMode.SEND
        return WorkflowMode.DRAFT_ONLY

    @staticmethod
    def is_send_enabled() -> bool:
        """Check if send mode is explicitly enabled."""
        return FeatureFlagManager.get_workflow_mode() == WorkflowMode.SEND

    @staticmethod
    def is_draft_only() -> bool:
        """Check if running in draft-only mode (default)."""
        return FeatureFlagManager.get_workflow_mode() == WorkflowMode.DRAFT_ONLY

    @staticmethod
    def enforce_draft_only() -> None:
        """Raise error if send mode is attempted without explicit enable."""
        if FeatureFlagManager.is_send_enabled():
            require_explicit = os.environ.get("REQUIRE_EXPLICIT_SEND", "true").lower()
            if require_explicit == "true":
                explicit_confirm = os.environ.get("CONFIRM_SEND_MODE", "")
                if explicit_confirm != "I_UNDERSTAND_EMAILS_WILL_BE_SENT":
                    raise RuntimeError(
                        "Send mode requires explicit confirmation. "
                        "Set CONFIRM_SEND_MODE='I_UNDERSTAND_EMAILS_WILL_BE_SENT' to proceed."
                    )

