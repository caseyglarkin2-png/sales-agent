"""Auto-approval rules and decision tracking models."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base, SafeJSON


class RuleType(str, Enum):
    """Types of auto-approval rules."""

    REPLIED_BEFORE = "replied_before"  # Recipient has replied to us before
    KNOWN_GOOD_RECIPIENT = "known_good_recipient"  # Email in approved whitelist
    HIGH_ICP_SCORE = "high_icp_score"  # High ideal customer profile match


class ApprovalDecision(str, Enum):
    """Auto-approval decision outcomes."""

    AUTO_APPROVED = "auto_approved"  # Draft automatically approved and sent
    NEEDS_REVIEW = "needs_review"  # Draft requires manual operator review
    # Note: We never auto-reject - borderline cases always go to manual review


class AutoApprovalRule(Base):
    """Auto-approval rule configuration.

    Defines simple if/else rules for automatically approving drafts
    without requiring manual operator review. No ML - just deterministic logic.
    """

    __tablename__ = "auto_approval_rules"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Rule identification
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="Type of rule (replied_before, etc.)"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Human-readable rule name")
    description: Mapped[Optional[str]] = mapped_column(
        Text, comment="Detailed description of what this rule checks"
    )

    # Rule configuration
    conditions: Mapped[Dict[str, Any]] = mapped_column(
        SafeJSON,
        nullable=False,
        default=dict,
        comment="Rule conditions as JSON (e.g., {'icp_score_min': 0.9, 'days_lookback': 90})",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Confidence score 0.0-1.0 (higher = safer rule)",
    )

    # Rule status
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Whether this rule is active"
    )
    priority: Mapped[int] = mapped_column(
        "priority",
        default=100,
        comment="Evaluation priority (lower = evaluated first)",
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), comment="User who created rule")

    def __repr__(self) -> str:
        return f"<AutoApprovalRule id={self.id} type={self.rule_type} enabled={self.enabled}>"


class ApprovedRecipient(Base):
    """Whitelist of known good email recipients.

    Populated from manually approved drafts that had positive outcomes.
    Used by the "known_good_recipient" auto-approval rule.
    """

    __tablename__ = "approved_recipients"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Recipient info
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="Recipient email address"
    )
    domain: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, comment="Email domain (e.g., 'example.com')"
    )

    # Tracking
    first_approved_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, comment="When first draft was approved"
    )
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(
        comment="When last email was sent to this recipient"
    )
    total_sends: Mapped[int] = mapped_column(default=1, comment="Total emails sent to this recipient")
    total_replies: Mapped[int] = mapped_column(default=0, comment="Total replies received")

    # Source tracking
    added_by: Mapped[Optional[str]] = mapped_column(
        String(255), comment="User who added to whitelist (or 'auto' for automated)"
    )
    source_draft_id: Mapped[Optional[str]] = mapped_column(
        String(255), comment="Draft ID that triggered whitelist addition"
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ApprovedRecipient email={self.email} sends={self.total_sends} replies={self.total_replies}>"


class AutoApprovalLog(Base):
    """Log of all auto-approval decisions for audit trail.

    Records every draft that went through auto-approval evaluation,
    the decision made, and the reasoning.
    """

    __tablename__ = "auto_approval_logs"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Draft reference
    draft_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Draft that was evaluated"
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Draft recipient"
    )

    # Decision
    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Decision outcome (auto_approved, needs_review)",
    )
    matched_rule_id: Mapped[Optional[str]] = mapped_column(
        String(36), comment="Rule ID that matched (null if no match)"
    )
    matched_rule_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment="Type of rule that matched"
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, comment="Confidence score of decision"
    )

    # Reasoning
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text, comment="Human-readable explanation of decision"
    )
    # Note: 'metadata' is reserved by SQLAlchemy, use 'decision_metadata' instead
    decision_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        SafeJSON, comment="Additional context (e.g., ICP score, reply history)"
    )

    # Audit
    evaluated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, index=True, comment="When evaluation occurred"
    )

    def __repr__(self) -> str:
        return f"<AutoApprovalLog draft={self.draft_id} decision={self.decision} rule={self.matched_rule_type}>"
