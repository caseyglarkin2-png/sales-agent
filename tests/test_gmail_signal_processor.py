"""Tests for GmailReplySignalProcessor."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.signal import Signal, SignalSource
from src.services.signal_processors.gmail import (
    GmailReplySignalProcessor,
    create_reply_signals_from_threads,
    _parse_from_header,
)


class TestGmailReplySignalProcessor:
    """Test GmailReplySignalProcessor."""

    @pytest.fixture
    def processor(self):
        return GmailReplySignalProcessor()

    @pytest.fixture
    def valid_reply_signal(self):
        return Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-abc123",
            payload={
                "thread_id": "thread-123",
                "message_id": "msg-456",
                "from_email": "prospect@company.com",
                "from_name": "John Prospect",
                "subject": "Re: Your proposal",
                "snippet": "Thanks for reaching out, I'd love to schedule a call.",
                "is_positive": True,
            },
            created_at=datetime.utcnow(),
        )

    def test_source_name(self, processor):
        """Test source name is gmail."""
        assert processor.source_name == "gmail"

    def test_can_handle_reply_received(self, processor, valid_reply_signal):
        """Test can handle reply_received events."""
        assert processor.can_handle(valid_reply_signal) is True

    def test_can_handle_thread_updated(self, processor):
        """Test can handle thread_updated events."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="thread_updated",
            source_id="thread-update-123",
            payload={"thread_id": "thread-123", "from_email": "test@test.com"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is True

    def test_cannot_handle_wrong_source(self, processor):
        """Test cannot handle non-Gmail signals."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.HUBSPOT,
            event_type="reply_received",
            source_id="reply-123",
            payload={"thread_id": "t-123", "from_email": "test@test.com"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is False

    def test_cannot_handle_wrong_event_type(self, processor):
        """Test cannot handle non-reply events."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="email_sent",
            source_id="sent-123",
            payload={"thread_id": "t-123"},
            created_at=datetime.utcnow(),
        )
        assert processor.can_handle(signal) is False

    @pytest.mark.asyncio
    async def test_validate_requires_thread_id(self, processor):
        """Test validation requires thread_id."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-test",
            payload={"from_email": "test@test.com"},  # Missing thread_id
            created_at=datetime.utcnow(),
        )
        assert await processor.validate(signal) is False

    @pytest.mark.asyncio
    async def test_validate_requires_from_email(self, processor):
        """Test validation requires from_email."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-test",
            payload={"thread_id": "thread-123"},  # Missing from_email
            created_at=datetime.utcnow(),
        )
        assert await processor.validate(signal) is False

    @pytest.mark.asyncio
    async def test_validate_passes_with_required_fields(self, processor, valid_reply_signal):
        """Test validation passes with required fields."""
        assert await processor.validate(valid_reply_signal) is True

    @pytest.mark.asyncio
    async def test_process_creates_command_queue_item(self, processor, valid_reply_signal):
        """Test process creates a command queue item."""
        result = await processor.process(valid_reply_signal)
        
        assert result is not None
        assert result.action_type == "schedule_meeting"  # "schedule a call" in snippet
        assert result.status == "pending"
        assert result.owner == "casey"

    @pytest.mark.asyncio
    async def test_process_includes_reply_info_in_context(self, processor, valid_reply_signal):
        """Test process includes reply info in action context."""
        result = await processor.process(valid_reply_signal)
        
        assert result is not None
        context = result.action_context
        assert context["thread_id"] == "thread-123"
        assert context["from_email"] == "prospect@company.com"
        assert context["from_name"] == "John Prospect"
        assert "schedule a call" in context["snippet"]

    @pytest.mark.asyncio
    async def test_process_calculates_aps(self, processor, valid_reply_signal):
        """Test process calculates APS score."""
        result = await processor.process(valid_reply_signal)
        
        assert result is not None
        assert 0 <= result.priority_score <= 1.0

    @pytest.mark.asyncio
    async def test_process_sets_due_by_for_positive_reply(self, processor, valid_reply_signal):
        """Test positive replies get short due_by."""
        result = await processor.process(valid_reply_signal)
        
        assert result is not None
        assert result.due_by > datetime.utcnow()
        # Positive reply should be within 2 hours
        assert result.due_by < datetime.utcnow() + timedelta(hours=3)

    @pytest.mark.asyncio
    async def test_process_meeting_keywords_get_schedule_action(self, processor):
        """Test meeting keywords trigger schedule_meeting action."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-meeting",
            payload={
                "thread_id": "thread-123",
                "from_email": "prospect@test.com",
                "from_name": "Test User",
                "snippet": "Let's schedule a call to discuss this further",
            },
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        
        assert result is not None
        assert result.action_type == "schedule_meeting"

    @pytest.mark.asyncio
    async def test_process_interest_keywords_get_follow_up_action(self, processor):
        """Test interest keywords trigger email_follow_up action."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-interest",
            payload={
                "thread_id": "thread-123",
                "from_email": "prospect@test.com",
                "from_name": "Test User",
                "snippet": "I'm interested in learning more about your pricing",
            },
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        
        assert result is not None
        assert result.action_type == "email_follow_up"

    @pytest.mark.asyncio
    async def test_process_unsubscribe_keywords_get_unsubscribe_action(self, processor):
        """Test unsubscribe keywords trigger unsubscribe_process action."""
        signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-unsub",
            payload={
                "thread_id": "thread-123",
                "from_email": "nope@test.com",
                "from_name": "Not Interested",
                "snippet": "Please unsubscribe me from your list",
                "is_positive": False,
            },
            created_at=datetime.utcnow(),
        )
        result = await processor.process(signal)
        
        assert result is not None
        assert result.action_type == "unsubscribe_process"

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
    async def test_negative_reply_has_lower_urgency(self, processor):
        """Test negative replies get lower priority."""
        positive_signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-pos",
            payload={
                "thread_id": "thread-123",
                "from_email": "happy@test.com",
                "from_name": "Happy User",
                "snippet": "This sounds great, let's talk!",
                "is_positive": True,
            },
            created_at=datetime.utcnow(),
        )
        
        negative_signal = Signal(
            id=str(uuid4()),
            source=SignalSource.GMAIL,
            event_type="reply_received",
            source_id="reply-neg",
            payload={
                "thread_id": "thread-456",
                "from_email": "sad@test.com",
                "from_name": "Sad User",
                "snippet": "Thanks but not interested at this time",
                "is_positive": False,
            },
            created_at=datetime.utcnow(),
        )
        
        pos_result = await processor.process(positive_signal)
        neg_result = await processor.process(negative_signal)
        
        assert pos_result is not None
        assert neg_result is not None
        assert pos_result.priority_score > neg_result.priority_score


class TestCreateReplySignalsFromThreads:
    """Test the helper function to create signals from threads."""

    def test_creates_signals_from_threads_with_replies(self):
        """Test creating signals from threads containing our messages and replies."""
        our_message_ids = ["our-msg-1", "our-msg-2"]
        threads = [
            {
                "id": "thread-1",
                "messages": [
                    {"id": "our-msg-1", "snippet": "Hey there"},
                    {
                        "id": "reply-1",
                        "snippet": "Thanks for reaching out!",
                        "internalDate": str(int(datetime.now().timestamp() * 1000)),
                        "payload": {
                            "headers": [
                                {"name": "From", "value": "John <john@test.com>"},
                                {"name": "Subject", "value": "Re: Hello"}
                            ]
                        }
                    }
                ]
            }
        ]
        
        signals = create_reply_signals_from_threads(threads, our_message_ids)
        
        assert len(signals) == 1
        assert signals[0].source == SignalSource.GMAIL
        assert signals[0].event_type == "reply_received"
        assert signals[0].payload["from_email"] == "john@test.com"
        assert signals[0].payload["from_name"] == "John"

    def test_skips_threads_without_our_messages(self):
        """Test threads without our messages are skipped."""
        our_message_ids = ["our-msg-1"]
        threads = [
            {
                "id": "thread-1",
                "messages": [
                    {"id": "other-msg-1"},
                    {"id": "other-msg-2"}
                ]
            }
        ]
        
        signals = create_reply_signals_from_threads(threads, our_message_ids)
        assert len(signals) == 0

    def test_skips_threads_with_no_reply(self):
        """Test threads with only our messages are skipped."""
        our_message_ids = ["our-msg-1"]
        threads = [
            {
                "id": "thread-1",
                "messages": [
                    {"id": "our-msg-1", "snippet": "Hey there"}
                ]
            }
        ]
        
        signals = create_reply_signals_from_threads(threads, our_message_ids)
        assert len(signals) == 0

    def test_filters_by_last_checked(self):
        """Test filtering by last_checked timestamp."""
        now = datetime.utcnow()
        old_time = int((now - timedelta(hours=2)).timestamp() * 1000)
        new_time = int((now - timedelta(minutes=5)).timestamp() * 1000)
        
        our_message_ids = ["our-msg-1", "our-msg-2"]
        threads = [
            {
                "id": "thread-old",
                "messages": [
                    {"id": "our-msg-1"},
                    {
                        "id": "old-reply",
                        "internalDate": str(old_time),
                        "payload": {"headers": [{"name": "From", "value": "old@test.com"}]}
                    }
                ]
            },
            {
                "id": "thread-new",
                "messages": [
                    {"id": "our-msg-2"},
                    {
                        "id": "new-reply",
                        "internalDate": str(new_time),
                        "payload": {"headers": [{"name": "From", "value": "new@test.com"}]}
                    }
                ]
            }
        ]
        
        last_checked = now - timedelta(hours=1)
        signals = create_reply_signals_from_threads(threads, our_message_ids, last_checked)
        
        # Only the new reply should be included
        assert len(signals) == 1
        assert signals[0].payload["from_email"] == "new@test.com"

    def test_handles_empty_threads_list(self):
        """Test handling empty threads list."""
        signals = create_reply_signals_from_threads([], ["msg-1"])
        assert len(signals) == 0


class TestParseFromHeader:
    """Test the _parse_from_header helper."""

    def test_parses_name_and_email(self):
        """Test parsing 'Name <email>' format."""
        name, email = _parse_from_header("John Doe <john@example.com>")
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_parses_quoted_name(self):
        """Test parsing quoted name format."""
        name, email = _parse_from_header('"John Doe" <john@example.com>')
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_parses_email_only(self):
        """Test parsing email-only format."""
        name, email = _parse_from_header("john@example.com")
        assert name == ""
        assert email == "john@example.com"

    def test_handles_invalid_format(self):
        """Test handling invalid format."""
        name, email = _parse_from_header("not an email")
        assert name == "Unknown"
        assert email == ""
