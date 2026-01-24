"""Tests for SignalToRecommendationService."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.models.signal import Signal, SignalSource
from src.services.signal_to_recommendation import (
    SignalToRecommendationService,
    ActionTypeMapping,
    SIGNAL_ACTION_MAPPINGS,
)


class TestSignalToRecommendationService:
    """Test SignalToRecommendationService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return SignalToRecommendationService()

    @pytest.fixture
    def form_signal(self):
        """Create a form submission signal."""
        return Signal(
            id="signal-form-001",
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={
                "email": "test@example.com",
                "name": "Test User",
                "company": "Test Corp",
                "form_id": "contact-form",
            },
            source_id="submission-001",
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def hubspot_deal_signal(self):
        """Create a HubSpot deal created signal."""
        return Signal(
            id="signal-hubspot-001",
            source=SignalSource.HUBSPOT,
            event_type="deal_created",
            payload={
                "deal_id": "deal-123",
                "deal_name": "Acme Corp - Enterprise",
                "deal_amount": 50000,
                "contact_email": "buyer@acme.com",
                "contact_name": "John Buyer",
            },
            source_id="deal-123",
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def gmail_reply_signal(self):
        """Create a Gmail reply signal."""
        return Signal(
            id="signal-gmail-001",
            source=SignalSource.GMAIL,
            event_type="reply_received",
            payload={
                "thread_id": "thread-abc",
                "message_id": "msg-xyz",
                "from_email": "prospect@company.com",
                "sender_name": "Jane Prospect",
                "subject": "Re: Your Proposal",
            },
            source_id="msg-xyz",
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def unknown_signal(self):
        """Create a signal with no mapping."""
        return Signal(
            id="signal-unknown-001",
            source=SignalSource.MANUAL,
            event_type="unknown_event",
            payload={"data": "test"},
            source_id="unknown-001",
            created_at=datetime.utcnow(),
        )

    # === Test get_action_type ===

    def test_get_action_type_form(self, service, form_signal):
        """Form submission maps to email_follow_up."""
        assert service.get_action_type(form_signal) == "email_follow_up"

    def test_get_action_type_hubspot_deal(self, service, hubspot_deal_signal):
        """HubSpot deal created maps to deal_outreach."""
        assert service.get_action_type(hubspot_deal_signal) == "deal_outreach"

    def test_get_action_type_gmail_reply(self, service, gmail_reply_signal):
        """Gmail reply maps to reply_response."""
        assert service.get_action_type(gmail_reply_signal) == "reply_response"

    def test_get_action_type_unknown(self, service, unknown_signal):
        """Unknown signal type returns None."""
        assert service.get_action_type(unknown_signal) is None

    # === Test get_mapping ===

    def test_get_mapping_returns_config(self, service, form_signal):
        """get_mapping returns ActionTypeMapping with correct values."""
        mapping = service.get_mapping(form_signal)
        assert mapping is not None
        assert mapping.action_type == "email_follow_up"
        assert mapping.default_urgency == 0.9
        assert mapping.default_effort == 0.2
        assert mapping.due_by_hours == 2

    def test_get_mapping_hubspot(self, service, hubspot_deal_signal):
        """HubSpot deal has correct mapping configuration."""
        mapping = service.get_mapping(hubspot_deal_signal)
        assert mapping is not None
        assert mapping.action_type == "deal_outreach"
        assert mapping.due_by_hours == 4

    # === Test extract_revenue_impact ===

    def test_extract_revenue_hubspot_deal_amount(self, service, hubspot_deal_signal):
        """HubSpot deal amount is normalized to 0-1 scale."""
        # $50,000 / $100,000 = 0.5
        revenue = service.extract_revenue_impact(hubspot_deal_signal)
        assert revenue == 0.5

    def test_extract_revenue_hubspot_large_deal(self, service):
        """Large deal amount is capped at 1.0."""
        signal = Signal(
            id="big-deal",
            source=SignalSource.HUBSPOT,
            event_type="deal_created",
            payload={"deal_amount": 200000},
            created_at=datetime.utcnow(),
        )
        revenue = service.extract_revenue_impact(signal)
        assert revenue == 1.0

    def test_extract_revenue_payload_override(self, service):
        """Explicit revenue_impact in payload is used."""
        signal = Signal(
            id="explicit-revenue",
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={"email": "test@test.com", "revenue_impact": 0.8},
            created_at=datetime.utcnow(),
        )
        revenue = service.extract_revenue_impact(signal)
        assert revenue == 0.8

    def test_extract_revenue_default(self, service, form_signal):
        """Default revenue is used when not specified."""
        # Form default is 0.5
        revenue = service.extract_revenue_impact(form_signal)
        assert revenue == 0.5

    # === Test extract_contact_info ===

    def test_extract_contact_form(self, service, form_signal):
        """Form signal extracts email, name, company."""
        contact = service.extract_contact_info(form_signal)
        assert contact["email"] == "test@example.com"
        assert contact["name"] == "Test User"
        assert contact["company"] == "Test Corp"

    def test_extract_contact_hubspot(self, service, hubspot_deal_signal):
        """HubSpot signal uses contact_* fields."""
        contact = service.extract_contact_info(hubspot_deal_signal)
        assert contact["email"] == "buyer@acme.com"
        assert contact["name"] == "John Buyer"

    def test_extract_contact_gmail(self, service, gmail_reply_signal):
        """Gmail signal uses from_email and sender_name."""
        contact = service.extract_contact_info(gmail_reply_signal)
        assert contact["email"] == "prospect@company.com"
        assert contact["name"] == "Jane Prospect"

    # === Test convert ===

    def test_convert_form_signal(self, service, form_signal):
        """Form signal converts to CommandQueueItem."""
        item = service.convert(form_signal)
        
        assert item is not None
        assert item.action_type == "email_follow_up"
        assert item.status == "pending"
        assert item.owner == "casey"
        assert item.action_context["lead_email"] == "test@example.com"
        assert item.action_context["signal_id"] == "signal-form-001"
        assert item.priority_score > 0

    def test_convert_hubspot_deal(self, service, hubspot_deal_signal):
        """HubSpot deal converts with correct action type."""
        item = service.convert(hubspot_deal_signal)
        
        assert item is not None
        assert item.action_type == "deal_outreach"
        assert item.action_context["lead_email"] == "buyer@acme.com"

    def test_convert_gmail_reply(self, service, gmail_reply_signal):
        """Gmail reply converts with high urgency."""
        item = service.convert(gmail_reply_signal)
        
        assert item is not None
        assert item.action_type == "reply_response"
        # Reply should be due within 1 hour
        time_until_due = (item.due_by - datetime.utcnow()).total_seconds()
        assert time_until_due <= 3600  # Within 1 hour

    def test_convert_unknown_returns_none(self, service, unknown_signal):
        """Unknown signal type returns None."""
        item = service.convert(unknown_signal)
        assert item is None

    def test_convert_with_override_urgency(self, service, form_signal):
        """Urgency override affects APS score."""
        item_default = service.convert(form_signal)
        item_override = service.convert(form_signal, override_urgency=0.3)
        
        # Lower urgency should result in lower priority score
        assert item_override.priority_score < item_default.priority_score

    def test_convert_with_additional_context(self, service, form_signal):
        """Additional context is merged into action_context."""
        item = service.convert(
            form_signal,
            additional_context={"custom_field": "custom_value", "campaign_id": "123"}
        )
        
        assert item.action_context["custom_field"] == "custom_value"
        assert item.action_context["campaign_id"] == "123"
        # Original context is preserved
        assert item.action_context["lead_email"] == "test@example.com"

    def test_convert_includes_aps_components(self, service, form_signal):
        """APS components are included in action_context."""
        item = service.convert(form_signal)
        
        aps_components = item.action_context.get("aps_components")
        assert aps_components is not None
        assert "revenue_impact" in aps_components
        assert "urgency" in aps_components
        assert "effort" in aps_components
        assert "strategic_value" in aps_components

    # === Test convert_with_recommendation ===

    def test_convert_with_recommendation_creates_both(self, service, form_signal):
        """Creates both CommandQueueItem and ActionRecommendation."""
        result = service.convert_with_recommendation(form_signal)
        
        assert result is not None
        item, recommendation = result
        
        assert item is not None
        assert recommendation is not None
        assert item.recommendation_id == recommendation.id

    def test_convert_with_recommendation_reasoning(self, service, form_signal):
        """Recommendation has meaningful reasoning."""
        result = service.convert_with_recommendation(form_signal)
        item, recommendation = result
        
        assert recommendation.reasoning is not None
        assert len(recommendation.reasoning) > 0
        assert "Test User" in recommendation.reasoning

    def test_convert_with_recommendation_metadata(self, service, form_signal):
        """Recommendation metadata includes signal info."""
        result = service.convert_with_recommendation(form_signal)
        item, recommendation = result
        
        assert recommendation.recommendation_metadata["signal_id"] == "signal-form-001"
        assert recommendation.recommendation_metadata["signal_source"] == "form"

    # === Test class methods ===

    def test_get_supported_signal_types(self):
        """Returns list of supported signal types."""
        types = SignalToRecommendationService.get_supported_signal_types()
        
        assert len(types) > 0
        assert ("form", "form_submitted") in types
        assert ("hubspot", "deal_created") in types
        assert ("gmail", "reply_received") in types

    def test_get_action_types(self):
        """Returns list of all action types."""
        action_types = SignalToRecommendationService.get_action_types()
        
        assert len(action_types) > 0
        assert "email_follow_up" in action_types
        assert "deal_outreach" in action_types
        assert "reply_response" in action_types

    # === Test custom mappings ===

    def test_custom_mappings(self, form_signal):
        """Service can use custom mappings."""
        custom_mappings = {
            (SignalSource.FORM, "form_submitted"): ActionTypeMapping(
                action_type="custom_action",
                default_urgency=0.5,
                default_effort=0.5,
                default_strategic_value=0.5,
                due_by_hours=12,
            ),
        }
        
        service = SignalToRecommendationService(mappings=custom_mappings)
        item = service.convert(form_signal)
        
        assert item.action_type == "custom_action"

    # === Test reasoning generation ===

    def test_reasoning_high_revenue(self, service):
        """High revenue generates appropriate reasoning."""
        signal = Signal(
            id="high-rev",
            source=SignalSource.HUBSPOT,
            event_type="deal_created",
            payload={
                "deal_amount": 90000,
                "contact_name": "Big Buyer",
                "contact_email": "big@corp.com",
            },
            created_at=datetime.utcnow(),
        )
        result = service.convert_with_recommendation(signal)
        _, recommendation = result
        
        assert "High revenue" in recommendation.reasoning

    def test_reasoning_urgent_reply(self, service, gmail_reply_signal):
        """Urgent reply generates time-sensitive reasoning."""
        result = service.convert_with_recommendation(gmail_reply_signal)
        _, recommendation = result
        
        assert "immediately" in recommendation.reasoning or "Reply received" in recommendation.reasoning


class TestActionTypeMappings:
    """Test the default action type mappings."""

    def test_all_mappings_have_required_fields(self):
        """All mappings have required configuration."""
        for key, mapping in SIGNAL_ACTION_MAPPINGS.items():
            assert mapping.action_type is not None
            assert 0 <= mapping.default_urgency <= 1
            assert 0 <= mapping.default_effort <= 1
            assert 0 <= mapping.default_strategic_value <= 1
            assert mapping.due_by_hours > 0
            assert mapping.owner is not None

    def test_form_mapping_urgency(self):
        """Form submissions have high urgency."""
        mapping = SIGNAL_ACTION_MAPPINGS[(SignalSource.FORM, "form_submitted")]
        assert mapping.default_urgency >= 0.8

    def test_gmail_reply_fastest_response(self):
        """Gmail replies have shortest due_by window."""
        gmail_mapping = SIGNAL_ACTION_MAPPINGS[(SignalSource.GMAIL, "reply_received")]
        
        # Gmail should be fastest
        for key, mapping in SIGNAL_ACTION_MAPPINGS.items():
            if key != (SignalSource.GMAIL, "reply_received"):
                assert gmail_mapping.due_by_hours <= mapping.due_by_hours
