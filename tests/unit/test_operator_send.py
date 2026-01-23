"""Tests for Operator Mode Send Integration"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.operator_mode import DraftQueue, DraftStatus


@pytest.fixture
def draft_queue():
    """Create a draft queue for testing"""
    return DraftQueue(approval_required=True)


@pytest.fixture
def sample_draft():
    """Sample approved draft ready to send"""
    return {
        "id": "draft_123",
        "recipient": "test@example.com",
        "subject": "Test Email",
        "body": "This is a test email. Unsubscribe at http://example.com/unsub",
        "metadata": {
            "body_html": "<p>This is a test email.</p><p>Unsubscribe at http://example.com/unsub</p>",
        },
        "status": DraftStatus.APPROVED.value,
        "approved_by": "operator@pesti.io",
        "approved_at": "2026-01-23T10:00:00",
    }


class TestSendDraft:
    """Tests for send_draft functionality"""

    @pytest.mark.asyncio
    async def test_send_approved_draft_success(self, draft_queue, sample_draft):
        """Should send an approved draft successfully"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        mock_gmail_result = {"id": "msg_123", "threadId": "thread_456"}

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = mock_gmail_result
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is True
        assert result["message_id"] == "msg_123"
        assert result["thread_id"] == "thread_456"
        assert "sent_at" in result

        updated_draft = await draft_queue.get_draft(sample_draft["id"])
        assert updated_draft["status"] == DraftStatus.SENT.value

    @pytest.mark.asyncio
    async def test_send_draft_not_found(self, draft_queue):
        result = await draft_queue.send_draft(
            draft_id="nonexistent",
            approved_by="operator@pesti.io",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_unapproved_draft(self, draft_queue, sample_draft):
        sample_draft["status"] = DraftStatus.PENDING_APPROVAL.value
        draft_queue._cache[sample_draft["id"]] = sample_draft

        result = await draft_queue.send_draft(
            draft_id=sample_draft["id"],
            approved_by="operator@pesti.io",
        )

        assert result["success"] is False
        assert "approved" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_draft_safety_check_failure(self, draft_queue):
        unsafe_draft = {
            "id": "draft_unsafe",
            "recipient": "test@example.com",
            "subject": "Your SSN",
            "body": "Your SSN is 123-45-6789",
            "metadata": {},
            "status": DraftStatus.APPROVED.value,
        }
        draft_queue._cache[unsafe_draft["id"]] = unsafe_draft

        result = await draft_queue.send_draft(
            draft_id=unsafe_draft["id"],
            approved_by="operator@pesti.io",
            require_safety_checks=True,
        )

        assert result["success"] is False
        assert "safety" in result["error"].lower()
        assert len(result["violations"]) > 0

        updated_draft = await draft_queue.get_draft(unsafe_draft["id"])
        assert updated_draft["status"] == DraftStatus.REJECTED.value
        assert "safety" in updated_draft["rejected_reason"].lower()

    @pytest.mark.asyncio
    async def test_send_draft_skip_safety_checks(self, draft_queue):
        unsafe_draft = {
            "id": "draft_unsafe2",
            "recipient": "test@example.com",
            "subject": "Test",
            "body": "SSN: 123-45-6789",
            "metadata": {},
            "status": DraftStatus.APPROVED.value,
        }
        draft_queue._cache[unsafe_draft["id"]] = unsafe_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=unsafe_draft["id"],
                    approved_by="operator@pesti.io",
                    require_safety_checks=False,
                )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_draft_gmail_failure(self, draft_queue, sample_draft):
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.side_effect = Exception("Gmail API error")
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "failed" in result["error"].lower()

        updated_draft = await draft_queue.get_draft(sample_draft["id"])
        assert "send_error" in updated_draft["metadata"]
        assert "send_error_at" in updated_draft["metadata"]

    @pytest.mark.asyncio
    async def test_send_draft_with_threading(self, draft_queue):
        threaded_draft = {
            "id": "draft_thread",
            "recipient": "test@example.com",
            "subject": "Re: Previous Email",
            "body": "This is a reply. Unsubscribe at http://example.com/unsub",
            "metadata": {
                "in_reply_to": "<previous@example.com>",
                "references": "<original@example.com> <previous@example.com>",
            },
            "status": DraftStatus.APPROVED.value,
        }
        draft_queue._cache[threaded_draft["id"]] = threaded_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_789", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=threaded_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is True
        mock_instance.send_email.assert_called_once()
        call_kwargs = mock_instance.send_email.call_args.kwargs
        assert call_kwargs["in_reply_to"] == "<previous@example.com>"
        assert call_kwargs["references"] == "<original@example.com> <previous@example.com>"

    @pytest.mark.asyncio
    async def test_send_draft_audit_trail(self, draft_queue, sample_draft):
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                with patch("src.operator_mode.logger") as mock_logger:
                    result = await draft_queue.send_draft(
                        draft_id=sample_draft["id"],
                        approved_by="operator@pesti.io",
                    )

                    assert result["success"] is True
                    mock_logger.info.assert_called()

                    log_calls = [str(call) for call in mock_logger.info.call_args_list]
                    send_log = [log for log in log_calls if "sent successfully" in log]
                    assert len(send_log) > 0
    @pytest.mark.asyncio
    async def test_send_draft_blocked_when_allow_real_sends_false(self, draft_queue, sample_draft):
        """Should block send when ALLOW_REAL_SENDS is False"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                allow_real_sends=False,  # DISABLED
                google_client_id="test_id",
                google_client_secret="test_secret",
                google_user_email="user@example.com",
            )

            result = await draft_queue.send_draft(
                draft_id=sample_draft["id"],
                approved_by="operator@pesti.io",
            )

        assert result["success"] is False
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_draft_allowed_when_allow_real_sends_true(self, draft_queue, sample_draft):
        """Should allow send when ALLOW_REAL_SENDS is True"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    allow_real_sends=True,  # ENABLED
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is True
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_draft_rate_limit_daily_exceeded(self, draft_queue, sample_draft):
        """Should block send when daily rate limit exceeded"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.rate_limiter.get_rate_limiter") as mock_limiter_getter:
            mock_limiter = AsyncMock()
            mock_limiter.check_can_send.return_value = (False, "Daily limit (20) reached")
            mock_limiter_getter.return_value = mock_limiter

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    allow_real_sends=True,
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "daily" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_draft_rate_limit_contact_weekly_exceeded(self, draft_queue, sample_draft):
        """Should block send when contact weekly rate limit exceeded"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.rate_limiter.get_rate_limiter") as mock_limiter_getter:
            mock_limiter = AsyncMock()
            mock_limiter.check_can_send.return_value = (
                False,
                "Contact weekly limit (2) reached",
            )
            mock_limiter_getter.return_value = mock_limiter

            with patch("src.config.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(
                    allow_real_sends=True,
                    google_client_id="test_id",
                    google_client_secret="test_secret",
                    google_user_email="user@example.com",
                )

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "contact" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_draft_records_rate_limit_usage(self, draft_queue, sample_draft):
        """Should record send in rate limiter after successful send"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.rate_limiter.get_rate_limiter") as mock_limiter_getter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (True, "OK")
                mock_limiter.record_send = AsyncMock()
                mock_limiter_getter.return_value = mock_limiter

                with patch("src.config.get_settings") as mock_settings:
                    mock_settings.return_value = MagicMock(
                        allow_real_sends=True,
                        google_client_id="test_id",
                        google_client_secret="test_secret",
                        google_user_email="user@example.com",
                    )

                    result = await draft_queue.send_draft(
                        draft_id=sample_draft["id"],
                        approved_by="operator@pesti.io",
                    )

        assert result["success"] is True
        # Verify record_send was called with the recipient
        mock_limiter.record_send.assert_called_once_with(sample_draft["recipient"])

    @pytest.mark.asyncio
    async def test_send_draft_persists_metadata(self, draft_queue, sample_draft):
        """Should persist send metadata to database"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.rate_limiter.get_rate_limiter") as mock_limiter_getter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (True, "OK")
                mock_limiter_getter.return_value = mock_limiter

                with patch("src.config.get_settings") as mock_settings:
                    mock_settings.return_value = MagicMock(
                        allow_real_sends=True,
                        google_client_id="test_id",
                        google_client_secret="test_secret",
                        google_user_email="user@example.com",
                    )

                    with patch.object(draft_queue, "_get_db") as mock_get_db:
                        mock_db = AsyncMock()
                        mock_db.record_draft_send = AsyncMock(return_value=True)
                        mock_get_db.return_value = mock_db

                        result = await draft_queue.send_draft(
                            draft_id=sample_draft["id"],
                            approved_by="operator@pesti.io",
                        )

        assert result["success"] is True
        # Verify record_draft_send was called
        mock_db.record_draft_send.assert_called_once()
        call_args = mock_db.record_draft_send.call_args
        assert call_args[0][0] == sample_draft["id"]  # draft_id
        assert "sent_at" in call_args[0][1]  # metadata with sent_at
        assert call_args[0][2] == "operator@pesti.io"  # approved_by