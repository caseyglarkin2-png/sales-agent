"""Command Queue models for CaseyOS.

The Command Queue is Casey's daily "Today's Moves" - prioritized actions
that drive revenue. Each item is scored by APS (Action Priority Score)
and includes full context about WHY it matters.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import String, Float, Text, ForeignKey
# from sqlalchemy.dialects.postgresql import JSONB (Replaced by SafeJSON)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, SafeJSON


class ActionType(str, Enum):
    """Types of actions Casey can take."""
    # Sales actions
    SEND_EMAIL = "send_email"
    BOOK_MEETING = "book_meeting"
    REVIEW_DEAL = "review_deal"
    SEND_PROPOSAL = "send_proposal"
    FOLLOW_UP = "follow_up"
    CHECK_IN = "check_in"
    PREP_MEETING = "prep_meeting"
    
    # Marketing Ops actions (Sprint 12a)
    CONTENT_REPURPOSE = "content_repurpose"
    SOCIAL_POST = "social_post"
    NEWSLETTER_DRAFT = "newsletter_draft"
    ASSET_CREATE = "asset_create"
    
    # Customer Success actions (Sprint 12b)
    CS_HEALTH_CHECK = "cs_health_check"
    RENEWAL_OUTREACH = "renewal_outreach"
    RISK_ESCALATION = "risk_escalation"
    ONBOARDING_FOLLOW_UP = "onboarding_follow_up"
    
    OTHER = "other"


class DomainType(str, Enum):
    """GTM domains for action categorization."""
    SALES = "sales"
    MARKETING = "marketing"
    CS = "cs"  # Customer Success


class QueueItemStatus(str, Enum):
    """Status of a queue item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    SNOOZED = "snoozed"


class ActionRecommendation(Base):
    """Recommendation with APS and explainability."""

    __tablename__ = "action_recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    aps_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    revenue_impact: Mapped[float] = mapped_column(Float, default=0.0)
    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    effort_score: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_score: Mapped[float] = mapped_column(Float, default=0.0)

    recommendation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(SafeJSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Relationship to queue items
    queue_items: Mapped[List["CommandQueueItem"]] = relationship(
        "CommandQueueItem", 
        back_populates="recommendation"
    )


class CommandQueueItem(Base):
    """Item in the daily command queue - Casey's "Today's Moves".
    
    Each item represents a prioritized action with full context:
    - WHO: Contact/Company/Deal from HubSpot
    - WHAT: Action type (send_email, book_meeting, etc.)
    - WHY: Reasoning + driver scores (urgency, revenue, effort)
    - WHEN: Due date + snooze capability
    """

    __tablename__ = "command_queue_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    
    # Human-readable context
    title: Mapped[str] = mapped_column(String(256), nullable=False)  # "Follow up with John at Acme"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # More context
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(SafeJSON, default=dict)
    
    # Domain categorization (Sprint 12)
    domain: Mapped[str] = mapped_column(String(32), index=True, default="sales")  # sales, marketing, cs

    # Priority scoring (0-100)
    priority_score: Mapped[float] = mapped_column(Float, index=True, nullable=False, default=50.0)
    
    # Explainability - WHY this action matters
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # "Opened email 3x this week"
    drivers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)  # {"urgency": 8, "revenue": 9}
    
    # HubSpot references for context
    contact_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    deal_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    owner: Mapped[str] = mapped_column(String(128), default="casey")  # User email
    
    # Timing
    due_by: Mapped[Optional[datetime]] = mapped_column(default=None)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    executed_at: Mapped[Optional[datetime]] = mapped_column(default=None)  # When action was taken
    
    # Outcome tracking
    outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=None)
    
    # Link to recommendation that generated this
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("action_recommendations.id", ondelete="SET NULL"),
        nullable=True, 
        index=True
    )
    recommendation: Mapped[Optional["ActionRecommendation"]] = relationship(
        "ActionRecommendation",
        back_populates="queue_items"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
