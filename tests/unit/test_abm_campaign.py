"""Unit tests for ABM Campaign models and API.

Sprint 62: ABM Campaigns
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.abm_campaign import (
    ABMCampaign,
    ABMCampaignAccount,
    ABMCampaignContact,
    ABMCampaignEmail,
    ABMCampaignStatus,
)
from src.campaigns.abm_email_generator import (
    ABMEmailContext,
    GeneratedEmail,
    generate_abm_email,
    calculate_personalization_score,
)


class TestABMCampaignModel:
    """Tests for ABM campaign model."""

    def test_campaign_to_dict(self):
        """Test campaign serialization."""
        campaign = ABMCampaign(
            id=uuid.uuid4(),
            name="Q1 Enterprise Push",
            description="Target enterprise accounts",
            status=ABMCampaignStatus.DRAFT.value,
            target_personas=["CEO", "VP Sales"],
            target_industries=["SaaS", "FinTech"],
            email_template_type="cold_outreach",
            total_accounts=10,
            total_contacts=30,
            emails_generated=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        result = campaign.to_dict()
        
        assert result["name"] == "Q1 Enterprise Push"
        assert result["status"] == "draft"
        assert result["target_personas"] == ["CEO", "VP Sales"]
        assert result["total_accounts"] == 10
        assert result["total_contacts"] == 30

    def test_account_to_dict(self):
        """Test account serialization."""
        account = ABMCampaignAccount(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            company_name="Acme Corp",
            company_domain="acme.com",
            company_industry="Technology",
            account_context={"pain_points": ["scaling", "efficiency"]},
            emails_generated=0,
            created_at=datetime.utcnow(),
        )
        
        result = account.to_dict()
        
        assert result["company_name"] == "Acme Corp"
        assert result["company_domain"] == "acme.com"
        assert result["account_context"]["pain_points"] == ["scaling", "efficiency"]

    def test_contact_to_dict(self):
        """Test contact serialization."""
        contact = ABMCampaignContact(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            email="john@acme.com",
            first_name="John",
            last_name="Doe",
            title="VP Sales",
            persona="VP Sales",
            created_at=datetime.utcnow(),
        )
        
        result = contact.to_dict()
        
        assert result["email"] == "john@acme.com"
        assert result["first_name"] == "John"
        assert result["persona"] == "VP Sales"

    def test_email_to_dict(self):
        """Test email serialization."""
        email = ABMCampaignEmail(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            subject="Quick question about Acme",
            body="Hi John, I noticed...",
            status="draft",
            personalization_score=75,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        result = email.to_dict()
        
        assert result["subject"] == "Quick question about Acme"
        assert result["status"] == "draft"
        assert result["personalization_score"] == 75


class TestABMEmailGenerator:
    """Tests for ABM email generator."""

    def test_calculate_personalization_score_full_context(self):
        """Test scoring with full context."""
        context = ABMEmailContext(
            first_name="John",
            title="VP Sales",
            persona="VP Sales",
            company_name="Acme Corp",
            company_industry="SaaS",
            pain_points=["scaling"],
            trigger_event="Series B funding",
            recent_news="Acquired startup",
        )
        
        score, elements = calculate_personalization_score(context)
        
        assert score >= 80  # High score with full context
        assert "first_name" in elements
        assert "company_name" in elements
        assert "pain_points" in elements
        assert "trigger_event" in elements

    def test_calculate_personalization_score_minimal_context(self):
        """Test scoring with minimal context."""
        context = ABMEmailContext(
            first_name="John",
            company_name="",
        )
        
        score, elements = calculate_personalization_score(context)
        
        assert score < 20  # Low score with minimal context
        assert "first_name" in elements
        assert len(elements) == 1

    def test_generate_abm_email_cold_outreach(self):
        """Test generating cold outreach email."""
        context = ABMEmailContext(
            first_name="John",
            last_name="Doe",
            email="john@acme.com",
            title="VP Sales",
            persona="VP Sales",
            company_name="Acme Corp",
            company_industry="SaaS",
            trigger_event="raised Series B",
        )
        
        result = generate_abm_email(context, "cold_outreach")
        
        assert isinstance(result, GeneratedEmail)
        assert "John" in result.subject or "Acme" in result.subject
        assert "John" in result.body
        assert "Acme" in result.body
        assert result.personalization_score > 0

    def test_generate_abm_email_follow_up(self):
        """Test generating follow-up email."""
        context = ABMEmailContext(
            first_name="Sarah",
            company_name="TechCo",
        )
        
        result = generate_abm_email(context, "follow_up")
        
        assert "Sarah" in result.subject or "follow" in result.subject.lower()
        assert "Sarah" in result.body

    def test_generate_abm_email_ceo_persona(self):
        """Test generating email for CEO persona."""
        context = ABMEmailContext(
            first_name="Alex",
            persona="CEO",
            company_name="StartupX",
        )
        
        result = generate_abm_email(context, "cold_outreach")
        
        assert "executive" in result.body.lower() or "time" in result.body.lower()

    def test_abm_context_to_dict(self):
        """Test context serialization."""
        context = ABMEmailContext(
            first_name="John",
            company_name="Acme",
            pain_points=["scaling"],
        )
        
        result = context.to_dict()
        
        assert result["first_name"] == "John"
        assert result["company_name"] == "Acme"
        assert result["pain_points"] == ["scaling"]


class TestABMCampaignStatus:
    """Tests for campaign status enum."""

    def test_status_values(self):
        """Test all status values are valid."""
        assert ABMCampaignStatus.DRAFT.value == "draft"
        assert ABMCampaignStatus.GENERATING.value == "generating"
        assert ABMCampaignStatus.READY.value == "ready"
        assert ABMCampaignStatus.ACTIVE.value == "active"
        assert ABMCampaignStatus.PAUSED.value == "paused"
        assert ABMCampaignStatus.COMPLETED.value == "completed"
