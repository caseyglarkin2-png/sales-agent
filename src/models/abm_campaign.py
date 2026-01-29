"""SQLAlchemy models for Account-Based Marketing campaigns."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base, SafeJSON


class ABMCampaignStatus(str, PyEnum):
    """ABM campaign status."""
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ABMCampaign(Base):
    """Account-Based Marketing campaign targeting multiple accounts with persona-based emails."""

    __tablename__ = "abm_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=ABMCampaignStatus.DRAFT.value)
    
    # Targeting configuration
    target_personas: Mapped[dict] = mapped_column(SafeJSON, default=list)  # ["CEO", "VP Sales", "Director Marketing"]
    target_industries: Mapped[Optional[dict]] = mapped_column(SafeJSON, nullable=True)
    
    # Content configuration
    email_template_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # cold_outreach, follow_up, etc.
    sequence_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Ownership
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Metrics (denormalized for performance)
    total_accounts: Mapped[int] = mapped_column(Integer, default=0)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    emails_generated: Mapped[int] = mapped_column(Integer, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    emails_opened: Mapped[int] = mapped_column(Integer, default=0)
    emails_replied: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    accounts: Mapped[List["ABMCampaignAccount"]] = relationship(
        "ABMCampaignAccount", back_populates="campaign", cascade="all, delete-orphan"
    )
    emails: Mapped[List["ABMCampaignEmail"]] = relationship(
        "ABMCampaignEmail", back_populates="campaign", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_abm_campaigns_status", "status"),
        Index("ix_abm_campaigns_owner", "owner_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "target_personas": self.target_personas or [],
            "target_industries": self.target_industries,
            "email_template_type": self.email_template_type,
            "sequence_id": str(self.sequence_id) if self.sequence_id else None,
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "total_accounts": self.total_accounts,
            "total_contacts": self.total_contacts,
            "emails_generated": self.emails_generated,
            "emails_sent": self.emails_sent,
            "emails_opened": self.emails_opened,
            "emails_replied": self.emails_replied,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "launched_at": self.launched_at.isoformat() if self.launched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ABMCampaignAccount(Base):
    """An account (company) targeted by an ABM campaign."""

    __tablename__ = "abm_campaign_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("abm_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    
    # Company reference (either HubSpot or manual)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Account-level context for personalization
    account_context: Mapped[Optional[dict]] = mapped_column(SafeJSON, nullable=True)
    # e.g., {"pain_points": ["scaling issues"], "trigger_event": "Series B funding"}
    
    # Status
    emails_generated: Mapped[int] = mapped_column(Integer, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign: Mapped["ABMCampaign"] = relationship("ABMCampaign", back_populates="accounts")
    contacts: Mapped[List["ABMCampaignContact"]] = relationship(
        "ABMCampaignContact", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_abm_campaign_accounts_campaign", "campaign_id"),
        Index("ix_abm_campaign_accounts_company", "company_id"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "company_id": str(self.company_id) if self.company_id else None,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "company_industry": self.company_industry,
            "account_context": self.account_context,
            "emails_generated": self.emails_generated,
            "emails_sent": self.emails_sent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ABMCampaignContact(Base):
    """A contact within an ABM campaign account."""

    __tablename__ = "abm_campaign_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("abm_campaign_accounts.id", ondelete="CASCADE"), nullable=False
    )
    
    # Contact reference (either HubSpot or manual)
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubspot_contacts.id"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # CEO, VP Sales, etc.
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    account: Mapped["ABMCampaignAccount"] = relationship("ABMCampaignAccount", back_populates="contacts")

    __table_args__ = (
        Index("ix_abm_campaign_contacts_account", "account_id"),
        Index("ix_abm_campaign_contacts_email", "email"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "account_id": str(self.account_id),
            "contact_id": str(self.contact_id) if self.contact_id else None,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "persona": self.persona,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ABMCampaignEmail(Base):
    """A generated email for an ABM campaign."""

    __tablename__ = "abm_campaign_emails"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("abm_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("abm_campaign_accounts.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("abm_campaign_contacts.id", ondelete="CASCADE"), nullable=False
    )
    
    # Email content
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, queued, sent, opened, replied
    queue_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Personalization score
    personalization_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    
    # Tracking
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign: Mapped["ABMCampaign"] = relationship("ABMCampaign", back_populates="emails")

    __table_args__ = (
        Index("ix_abm_campaign_emails_campaign", "campaign_id"),
        Index("ix_abm_campaign_emails_status", "status"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "account_id": str(self.account_id),
            "contact_id": str(self.contact_id),
            "subject": self.subject,
            "body": self.body,
            "status": self.status,
            "queue_item_id": str(self.queue_item_id) if self.queue_item_id else None,
            "personalization_score": self.personalization_score,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
