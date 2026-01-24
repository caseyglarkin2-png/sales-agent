"""Tests for FormSubmissionSignalProcessor."""
import pytest
from datetime import datetime

from src.models.signal import Signal, SignalSource
from src.services.signal_processors.form import FormSubmissionSignalProcessor


class TestFormSubmissionSignalProcessor:
    """Test FormSubmissionSignalProcessor."""

    @pytest.fixture
    def processor(self):
        return FormSubmissionSignalProcessor()

    @pytest.fixture
    def valid_form_signal(self):
        return Signal(
            id="test-signal-123",
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={
                "email": "lead@example.com",
                "name": "Test Lead",
                "company": "Test Corp",
            },
            created_at=datetime.utcnow(),
        )

    def test_source_name(self, processor):
        """Source name should be 'form'."""
        assert processor.source_name == "form"

    def test_can_handle_form_submitted(self, processor, valid_form_signal):
        """Should handle form_submitted events from FORM source."""
        assert processor.can_handle(valid_form_signal) is True

    def test_cannot_handle_wrong_source(self, processor):
        """Should not handle signals from other sources."""
        signal = Signal(
            source=SignalSource.HUBSPOT,
            event_type="form_submitted",
            payload={"email": "test@example.com"},
        )
        assert processor.can_handle(signal) is False

    def test_cannot_handle_wrong_event_type(self, processor):
        """Should not handle non-form_submitted events."""
        signal = Signal(
            source=SignalSource.FORM,
            event_type="other_event",
            payload={"email": "test@example.com"},
        )
        assert processor.can_handle(signal) is False

    @pytest.mark.asyncio
    async def test_validate_requires_email(self, processor):
        """Validation should require email in payload."""
        signal_no_email = Signal(
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={"name": "No Email Lead"},
        )
        assert await processor.validate(signal_no_email) is False

    @pytest.mark.asyncio
    async def test_validate_passes_with_email(self, processor, valid_form_signal):
        """Validation should pass with email present."""
        assert await processor.validate(valid_form_signal) is True

    @pytest.mark.asyncio
    async def test_process_creates_command_queue_item(self, processor, valid_form_signal):
        """Processing should create a command queue item."""
        item = await processor.process(valid_form_signal)
        
        assert item is not None
        assert item.action_type == "email_follow_up"
        assert item.status == "pending"
        assert item.owner == "casey"

    @pytest.mark.asyncio
    async def test_process_includes_lead_info_in_context(self, processor, valid_form_signal):
        """Command queue item should include lead info in context."""
        item = await processor.process(valid_form_signal)
        
        assert item.action_context["lead_email"] == "lead@example.com"
        assert item.action_context["lead_name"] == "Test Lead"
        assert item.action_context["lead_company"] == "Test Corp"
        assert item.action_context["signal_id"] == "test-signal-123"

    @pytest.mark.asyncio
    async def test_process_sets_due_by(self, processor, valid_form_signal):
        """Command queue item should have due_by set (within 2 hours)."""
        item = await processor.process(valid_form_signal)
        
        assert item.due_by is not None
        # Due by should be in the future
        assert item.due_by > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_process_calculates_aps(self, processor, valid_form_signal):
        """Command queue item should have priority_score from APS."""
        item = await processor.process(valid_form_signal)
        
        # priority_score should be between 0 and 1 (APS / 100)
        assert 0 <= item.priority_score <= 1.0

    @pytest.mark.asyncio
    async def test_process_returns_none_for_invalid_signal(self, processor):
        """Processing invalid signal should return None."""
        signal = Signal(
            source=SignalSource.HUBSPOT,  # Wrong source
            event_type="form_submitted",
            payload={"email": "test@example.com"},
        )
        item = await processor.process(signal)
        assert item is None

    @pytest.mark.asyncio
    async def test_process_returns_none_for_missing_email(self, processor):
        """Processing signal without email should return None."""
        signal = Signal(
            source=SignalSource.FORM,
            event_type="form_submitted",
            payload={"name": "No Email"},
        )
        item = await processor.process(signal)
        assert item is None
