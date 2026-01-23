"""
Feature flag system for controlling DRAFT_ONLY vs SEND mode with safety gates.

This module provides runtime toggles and validation for critical features,
with emphasis on production safety and auditability.
"""
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OperationMode(str, Enum):
    """Workflow operation modes."""
    DRAFT_ONLY = "draft_only"
    SEND = "send"


# Backwards compatibility
class WorkflowMode(Enum):
    """Workflow execution mode (legacy)."""
    DRAFT_ONLY = "draft_only"
    SEND = "send"


class FeatureFlagError(Exception):
    """Raised when feature flag validation fails."""
    pass


class SendModeConfig(BaseModel):
    """Configuration for SEND mode with safety constraints."""
    enabled: bool = False
    operator_approval_required: bool = True
    allowlist_emails: list[str] = []
    max_sends_per_hour: int = 100
    circuit_breaker_error_threshold: float = 0.10  # 10%
    

class FeatureFlagManager:
    """
    Manages feature flags with runtime toggles and audit trail.
    
    Key responsibilities:
    - Validate environment-specific mode constraints
    - Provide kill switch for emergency shutoff
    - Track mode changes with attribution
    - Enforce circuit breaker on error rates
    """
    
    def __init__(self, flags: Optional[dict] = None):
        """Initialize feature flag manager."""
        from src.config import get_settings
        self.settings = get_settings()
        self.flags = flags or {}
        self._send_mode_override: Optional[bool] = None
        self._mode_change_history: list[dict] = []
        self._recent_sends: list[dict] = []
        
    def is_send_mode_enabled(self) -> bool:
        """
        Check if SEND mode is currently enabled.
        
        Returns:
            True if SEND mode is active, False if DRAFT_ONLY
            
        Raises:
            FeatureFlagError: If configuration is invalid
        """
        # Check for kill switch override (takes precedence)
        if self._send_mode_override is not None:
            return self._send_mode_override
            
        # Check config flags
        if self.settings.MODE_DRAFT_ONLY:
            return False
            
        # SEND mode requires explicit enablement
        if not self.settings.ALLOW_AUTO_SEND:
            return False
            
        # Production environment check
        if self.settings.API_ENV != "production":
            logger.warning(
                f"SEND mode attempted in non-production environment: {self.settings.API_ENV}"
            )
            raise FeatureFlagError(
                f"SEND mode not allowed in {self.settings.API_ENV} environment"
            )
            
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.error("Circuit breaker OPEN - SEND mode disabled due to high error rate")
            return False
            
        return True
        
    def validate_send_mode(self) -> None:
        """
        Validate SEND mode configuration (raises on invalid).
        
        Used at startup to fail-fast on misconfiguration.
        
        Raises:
            FeatureFlagError: If SEND mode is improperly configured
        """
        if not self.is_send_mode_enabled():
            return  # DRAFT_ONLY is always valid
            
        # If SEND mode enabled, validate all requirements
        if not self.settings.ALLOW_AUTO_SEND:
            raise FeatureFlagError("SEND mode requires ALLOW_AUTO_SEND=true")
            
        if self.settings.API_ENV != "production":
            raise FeatureFlagError(
                f"SEND mode only allowed in production (current: {self.settings.API_ENV})"
            )
            
        logger.warning(
            "⚠️  SEND MODE ENABLED - Emails will be sent automatically. "
            "Use kill switch endpoint to disable: POST /api/admin/flags/send-mode/disable"
        )
        
    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode."""
        return OperationMode.SEND if self.is_send_mode_enabled() else OperationMode.DRAFT_ONLY
        
    def disable_send_mode(self, operator: str, reason: str) -> dict:
        """
        Emergency kill switch - disable SEND mode immediately.
        
        Args:
            operator: Name/email of operator executing kill switch
            reason: Reason for disabling (logged to audit trail)
            
        Returns:
            Confirmation dict with timestamp and old/new state
        """
        old_state = self.is_send_mode_enabled()
        self._send_mode_override = False
        
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operator": operator,
            "reason": reason,
            "old_state": "SEND" if old_state else "DRAFT_ONLY",
            "new_state": "DRAFT_ONLY",
            "action": "kill_switch_activated"
        }
        
        self._mode_change_history.append(change_record)
        
        logger.critical(
            f"🚨 KILL SWITCH ACTIVATED by {operator}: {reason}. "
            f"SEND mode disabled immediately."
        )
        
        return change_record
        
    def enable_send_mode(self, operator: str, reason: str) -> dict:
        """
        Enable SEND mode (requires validation).
        
        Args:
            operator: Name/email of operator enabling mode
            reason: Justification for enabling
            
        Returns:
            Confirmation dict
            
        Raises:
            FeatureFlagError: If environment/config invalid for SEND mode
        """
        # Validate environment first
        if self.settings.API_ENV != "production":
            raise FeatureFlagError(
                f"Cannot enable SEND mode in {self.settings.API_ENV} environment"
            )
            
        old_state = self.is_send_mode_enabled()
        self._send_mode_override = True
        
        change_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "operator": operator,
            "reason": reason,
            "old_state": "SEND" if old_state else "DRAFT_ONLY",
            "new_state": "SEND",
            "action": "send_mode_enabled"
        }
        
        self._mode_change_history.append(change_record)
        
        logger.warning(
            f"⚠️  SEND MODE ENABLED by {operator}: {reason}. "
            f"Emails will be sent automatically."
        )
        
        return change_record
        
    def get_mode_history(self) -> list[dict]:
        """Get mode change audit trail."""
        return self._mode_change_history.copy()
        
    def record_send_attempt(self, success: bool, email: str, error: Optional[str] = None):
        """
        Record send attempt for circuit breaker tracking.
        
        Args:
            success: Whether send succeeded
            email: Recipient email
            error: Error message if failed
        """
        self._recent_sends.append({
            "timestamp": datetime.utcnow(),
            "success": success,
            "email": email,
            "error": error
        })
        
        # Keep only last hour of sends
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        self._recent_sends = [
            s for s in self._recent_sends 
            if s["timestamp"] > one_hour_ago
        ]
        
    def _is_circuit_breaker_open(self) -> bool:
        """
        Check if circuit breaker should open due to high error rate.
        
        Returns:
            True if error rate exceeds threshold (SEND mode should be disabled)
        """
        if len(self._recent_sends) < 10:
            return False  # Need minimum sample size
            
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent = [s for s in self._recent_sends if s["timestamp"] > one_hour_ago]
        
        if not recent:
            return False
            
        error_count = sum(1 for s in recent if not s["success"])
        error_rate = error_count / len(recent)
        
        threshold = 0.10  # 10% error rate
        if error_rate > threshold:
            logger.error(
                f"Circuit breaker threshold exceeded: {error_rate:.1%} error rate "
                f"({error_count}/{len(recent)} sends failed in last hour)"
            )
            return True
            
        return False
        
    def get_circuit_breaker_status(self) -> dict:
        """Get current circuit breaker metrics."""
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent = [s for s in self._recent_sends if s["timestamp"] > one_hour_ago]
        
        if not recent:
            return {
                "status": "closed",
                "total_sends": 0,
                "error_rate": 0.0,
                "threshold": 0.10
            }
            
        error_count = sum(1 for s in recent if not s["success"])
        error_rate = error_count / len(recent)
        
        return {
            "status": "open" if self._is_circuit_breaker_open() else "closed",
            "total_sends": len(recent),
            "error_count": error_count,
            "error_rate": error_rate,
            "threshold": 0.10,
            "sample_window": "1 hour"
        }
    
    # Legacy compatibility methods
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled (legacy)."""
        return self.flags.get(flag_name, False)

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Set a feature flag (legacy)."""
        self.flags[flag_name] = enabled
        logger.info(f"Set feature flag '{flag_name}' to {enabled}")

    def get_all_flags(self) -> dict:
        """Get all feature flags (legacy)."""
        return self.flags.copy()

    @staticmethod
    def get_workflow_mode() -> WorkflowMode:
        """Get current workflow mode from environment (legacy)."""
        import os
        mode = os.environ.get("WORKFLOW_MODE", "draft_only").lower()
        if mode == "send":
            return WorkflowMode.SEND
        return WorkflowMode.DRAFT_ONLY

    @staticmethod
    def is_send_enabled() -> bool:
        """Check if send mode is explicitly enabled (legacy)."""
        return FeatureFlagManager.get_workflow_mode() == WorkflowMode.SEND

    @staticmethod
    def is_draft_only() -> bool:
        """Check if running in draft-only mode (legacy)."""
        return FeatureFlagManager.get_workflow_mode() == WorkflowMode.DRAFT_ONLY

    @staticmethod
    def enforce_draft_only() -> None:
        """Raise error if send mode is attempted without explicit enable (legacy)."""
        import os
        if FeatureFlagManager.is_send_enabled():
            require_explicit = os.environ.get("REQUIRE_EXPLICIT_SEND", "true").lower()
            if require_explicit == "true":
                explicit_confirm = os.environ.get("CONFIRM_SEND_MODE", "")
                if explicit_confirm != "I_UNDERSTAND_EMAILS_WILL_BE_SENT":
                    raise RuntimeError(
                        "Send mode requires explicit confirmation. "
                        "Set CONFIRM_SEND_MODE='I_UNDERSTAND_EMAILS_WILL_BE_SENT' to proceed."
                    )

