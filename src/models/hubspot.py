"""SQLAlchemy models for HubSpot entities."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.db import Base


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class HubSpotCompany(Base):
    """HubSpot company model."""

    __tablename__ = "hubspot_companies"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hubspot_company_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(512), nullable=False)
    domain = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    custom_properties = Column(JSONType, nullable=True)
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_hubspot_companies_domain", "domain"),)


class HubSpotContact(Base):
    """HubSpot contact model."""

    __tablename__ = "hubspot_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hubspot_contact_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    firstname = Column(String(255), nullable=True)
    lastname = Column(String(255), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True)
    custom_properties = Column(JSONType, nullable=True)
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_hubspot_contacts_email", "email"),)


class HubSpotDeal(Base):
    """HubSpot deal model."""

    __tablename__ = "hubspot_deals"

    id = Column(UUID(as_uuid=True), primary_key=True)
    hubspot_deal_id = Column(String(255), unique=True, nullable=False, index=True)
    dealname = Column(String(512), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True)
    stage = Column(String(255), nullable=True)
    amount = Column(String(255), nullable=True)
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class HubSpotFormSubmission(Base):
    """HubSpot form submission model."""

    __tablename__ = "hubspot_form_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    submission_id = Column(String(255), unique=True, nullable=False, index=True)
    form_id = Column(String(255), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_contacts.id"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("hubspot_companies.id"), nullable=True)
    fields = Column(JSONType, nullable=True)
    submitted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_hubspot_form_submissions_form_id_submitted", "form_id", "submitted_at"),
    )
