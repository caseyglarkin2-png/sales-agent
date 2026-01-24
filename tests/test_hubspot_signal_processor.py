"""Tests for HubSpotDealSignalProcessor."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.services.signal_processors.hubspot import (
    HubSpotDealSignalProcessor,
    create_deal_signals_from_api_response,
    DEAL_STAGE_URGENCY,
    DEAL_STAGE_ACTION,
)


class TestHubSpotDealSignalProcessor:
    """Test HubSpotDealSignalProcessor."""

    @pytest.fixture
    def processor(self):
        return HubSpotDealSignalProcessor()

    @pytest.fixture
    def valid_deal_signal(self):
        return Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-123",
            payload={
                "deal_id": "123",
                "deal_name": "Acme Corp Deal",
                "deal_stage": "qualifiedtobuy",
                "amount": 50000,
                "company_name": "Acme Corp",
                "contact_email": "john@acme.com",
            },
            created_at=datetime.utcnow(),
        )

    def test_source_name(self, processor):
        """Test source name is hubspot."""
        assert processor.source_name == "hubspot"

    def test_can_handle_deal_stage_changed(self, processor, valid_deal_signal):
        """Test can handle deal_stage_changed events."""
        assert processor.can_handle(valid_deal_signal) is True

    def test_can_handle_deal_created(self, processor):
        """Test can handle deal_created events."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_created",
            source_id="deal-456",
            payload={"deal_id": "456", "deal_name": "New Deal"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is True

    def test_can_handle_deal_amount_changed(self, processor):
        """Test can handle deal_amount_changed events."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_amount_changed",
            source_id="deal-789",
            payload={"deal_id": "789", "deal_name": "Updated Deal"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is True

    def test_cannot_handle_wrong_source(self, processor):
        """Test cannot handle non-HubSpot signals."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.FORM,
            event_type="deal_stage_changed",
            source_id="form-123",
            payload={"deal_id": "123", "deal_name": "Test"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is False

    def test_cannot_handle_wrong_event_type(self, processor):
        """Test cannot handle non-deal events."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="contact_created",
            source_id="contact-123",
            payload={"contact_id": "123"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is False

    @pytest.mark.asyncio
    async def test_validate_requires_deal_id(self, processor):
        """Test validation requires deal_id."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-test",
            payload={"deal_name": "Test Deal"},  # Missing deal_id
            created_at=datetime.utcnow(),
        )
        assert await processor.validate(signal) is False

    @pytest.mark.asyncio
    async def test_validate_requires_deal_name(self, processor):
        """Test validation requires deal_name."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-test",
            payload={"deal_id": "123"},  # Missing deal_name
            created_at=datetime.utcnow(),
        )
        assert await processor.validate(signal) is False

    @pytest.mark.asyncio
    async def test_validate_passes_with_required_fields(self, processor, valid_deal_signal):
        """Test validation passes with required fields."""
        assert await processor.validate(valid_deal_signal) is True

    @pytest.mark.asyncio
    async def test_process_creates_command_queue_item(self, processor, valid_deal_signal):
        """Test process creates a command queue item."""
        result = await processor.process(valid_deal_signal)
        
        assert result is not None
        assert result.action_type == "email_follow_up"  # qualifiedtobuy -> email_follow_up
        assert result.status == "pending"
        assert result.owner == "casey"

    @pytest.mark.asyncio
    async def test_process_includes_deal_info_in_context(self, processor, valid_deal_signal):
        """Test process includes deal info in action context."""
        result = await processor.process(valid_deal_signal)
        
        assert result is not None
        context = result.action_context
        assert context["deal_id"] == "123"
        assert context["deal_name"] == "Acme Corp Deal"
        assert context["deal_stage"] == "qualifiedtobuy"
        assert context["deal_amount"] == 50000
        assert context["company_name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_process_calculates_aps(self, processor, valid_deal_signal):
        """Test process calculates APS score."""
        result = await processor.process(valid_deal_signal)
        
        assert result is not None
        assert 0 <= result.priority_score <= 1.0

    @pytest.mark.asyncio
    async def test_process_sets_due_by(self, processor, valid_deal_signal):
        """Test process sets due_by based on urgency."""
        result = await processor.process(valid_deal_signal)
        
        assert result is not None
        assert result.due_by > datetime.utcnow()
        # qualifiedtobuy should be within 4 hours
        assert result.due_by < datetime.utcnow() + timedelta(hours=5)

    @pytest.mark.asyncio
    async def test_process_contract_sent_is_urgent(self, processor):
        """Test contract sent deals have short due_by."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-hot",
            payload={
                "deal_id": "hot-123",
                "deal_name": "Hot Deal",
                "deal_stage": "contractsent",
                "amount": 100000,
            },
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        
        assert result is not None
        # Contract sent should be within 1 hour
        assert result.due_by < datetime.utcnow() + timedelta(hours=2)

    @pytest.mark.asyncio
    async def test_process_deal_created_gets_research_action(self, processor):
        """Test new deals get deal_research action type."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_created",
            source_id="deal-new",
            payload={
                "deal_id": "new-123",
                "deal_name": "New Deal",
                "deal_stage": "appointmentscheduled",
                "amount": 25000,
            },
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        
        assert result is not None
        assert result.action_type == "deal_research"

    @pytest.mark.asyncio
    async def test_process_returns_none_for_invalid_signal(self, processor):
        """Test process returns None for signals it can't handle."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.FORM,
            event_type="form_submitted",
            source_id="form-123",
            payload={"email": "test@test.com"},
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_high_value_deal_gets_high_priority(self, processor):
        """Test high value deals get higher priority scores."""
        low_value_signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-low",
            payload={
                "deal_id": "low-123",
                "deal_name": "Small Deal",
                "deal_stage": "qualifiedtobuy",
                "amount": 1000,
            },
            created_at=datetime.utcnow(),
        )
        
        high_value_signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="deal_stage_changed",
            source_id="deal-high",
            payload={
                "deal_id": "high-123",
                "deal_name": "Big Deal",
                "deal_stage": "qualifiedtobuy",
                "amount": 100000,
            },
            created_at=datetime.utcnow(),
        )
        
        low_result = await processor.process(low_value_signal)
        high_result = await processor.process(high_value_signal)
        
        assert low_result is not None
        assert high_result is not None
        assert high_result.priority_score > low_result.priority_score


class TestCreateDealSignalsFromApiResponse:
    """Test the helper function to create signals from API response."""

    def test_creates_signals_from_deals(self):
        """Test creating signals from deal list."""
        deals = [
            {
                "id": "123",
                "properties": {
                    "dealname": "Deal 1",
                    "dealstage": "qualifiedtobuy",
                    "amount": "50000",
                }
            },
            {
                "id": "456",
                "properties": {
                    "dealname": "Deal 2",
                    "dealstage": "contractsent",
                    "amount": "75000",
                }
            }
        ]
        
        signals = create_deal_signals_from_api_response(deals)
        
        assert len(signals) == 2
        assert signals[0].source == SignalSource.HUBSPOT
        assert signals[0].event_type == "deal_stage_changed"
        assert signals[0].payload["deal_id"] == "123"

    def test_filters_by_last_checked(self):
        """Test filtering deals by last_checked timestamp."""
        now = datetime.utcnow()
        old_time = (now - timedelta(hours=2)).isoformat() + "Z"
        new_time = (now - timedelta(minutes=5)).isoformat() + "Z"
        
        deals = [
            {
                "id": "old",
                "properties": {
                    "dealname": "Old Deal",
                    "hs_lastmodifieddate": old_time,
                    "dealstage": "qualifiedtobuy",
                }
            },
            {
                "id": "new",
                "properties": {
                    "dealname": "New Deal",
                    "hs_lastmodifieddate": new_time,
                    "dealstage": "contractsent",
                }
            }
        ]
        
        last_checked = now - timedelta(hours=1)
        signals = create_deal_signals_from_api_response(deals, last_checked)
        
        # Only the new deal should be included
        assert len(signals) == 1
        assert signals[0].payload["deal_id"] == "new"

    def test_handles_missing_properties(self):
        """Test handling deals with missing properties."""
        deals = [
            {
                "id": "minimal",
                "properties": {
                    "dealname": "Minimal Deal",
                }
            }
        ]
        
        signals = create_deal_signals_from_api_response(deals)
        
        assert len(signals) == 1
        assert signals[0].payload["deal_name"] == "Minimal Deal"
        assert signals[0].payload["amount"] == 0  # Default

    def test_handles_empty_deals_list(self):
        """Test handling empty deals list."""
        signals = create_deal_signals_from_api_response([])
        assert len(signals) == 0
