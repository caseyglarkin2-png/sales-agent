"""Tests for Operator Mode Send Integration - ALLOW_REAL_SENDS and Rate Limiting"""

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


def mock_settings(allow_real_sends=True, max_per_day=20, max_per_week=2):
    """Helper to create properly configured mock settings"""
    return MagicMock(
        allow_real_sends=allow_real_sends,
        max_emails_per_day=max_per_day,
        max_emails_per_week=max_per_week,
        google_client_id="test_id",
        google_client_secret="test_secret",
        google_user_email="user@example.com",
    )


class TestAllowRealSends:
    """Tests for ALLOW_REAL_SENDS feature flag"""

    @pytest.mark.asyncio
    async def test_send_blocked_when_disabled(self, draft_queue, sample_draft):
        """Should block send when ALLOW_REAL_SENDS is False"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings(allow_real_sends=False)

            result = await draft_queue.send_draft(
                draft_id=sample_draft["id"],
                approved_by="operator@pesti.io",
            )

        assert result["success"] is False
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_allowed_when_enabled(self, draft_queue, sample_draft):
        """Should allow send when ALLOW_REAL_SENDS is True"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.config.get_settings") as mock_get_settings:
                mock_get_settings.return_value = mock_settings(allow_real_sends=True)

                with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                    mock_limiter = AsyncMock()
                    mock_limiter.check_can_send.return_value = (True, "OK")
                    mock_limiter.record_send = AsyncMock()
                    mock_get_limiter.return_value = mock_limiter

                    result = await draft_queue.send_draft(
                        draft_id=sample_draft["id"],
                        approved_by="operator@pesti.io",
                    )

        assert result["success"] is True
        assert "message_id" in result


class TestRateLimitEnforcement:
    """Tests for rate limit checks at send time"""

    @pytest.mark.asyncio
    async def test_daily_limit_enforced(self, draft_queue, sample_draft):
        """Should block send when daily rate limit exceeded"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_limiter = AsyncMock()
            mock_limiter.check_can_send.return_value = (False, "Daily limit (20) reached")
            mock_get_limiter.return_value = mock_limiter

            with patch("src.config.get_settings") as mock_get_settings:
                mock_get_settings.return_value = mock_settings(allow_real_sends=True)

                # Don't need to mock GmailConnector since we'll return before reaching it
                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "daily" in result["error"].lower()
        # Verify check_can_send was called
        mock_get_limiter.return_value.check_can_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_contact_weekly_limit_enforced(self, draft_queue, sample_draft):
        """Should block send when contact weekly rate limit exceeded"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
            mock_limiter = AsyncMock()
            mock_limiter.check_can_send.return_value = (
                False,
                "Contact weekly limit (2) reached",
            )
            mock_get_limiter.return_value = mock_limiter

            with patch("src.config.get_settings") as mock_get_settings:
                mock_get_settings.return_value = mock_settings(allow_real_sends=True)

                result = await draft_queue.send_draft(
                    draft_id=sample_draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "contact" in result["error"].lower()
        # Verify check_can_send was called
        mock_get_limiter.return_value.check_can_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_records_usage(self, draft_queue, sample_draft):
        """Should record send in rate limiter after successful send"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (True, "OK")
                mock_limiter.record_send = AsyncMock()
                mock_get_limiter.return_value = mock_limiter

                with patch("src.config.get_settings") as mock_get_settings:
                    mock_get_settings.return_value = mock_settings(allow_real_sends=True)

                    result = await draft_queue.send_draft(
                        draft_id=sample_draft["id"],
                        approved_by="operator@pesti.io",
                    )

        assert result["success"] is True
        # Verify record_send was called with the recipient
        mock_get_limiter.return_value.record_send.assert_called_once_with(sample_draft["recipient"])


class TestMetadataPersistence:
    """Tests for persisting send metadata to database"""

    @pytest.mark.asyncio
    async def test_persists_send_metadata(self, draft_queue, sample_draft):
        """Should persist send metadata to database"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
            MockGmail.return_value = mock_instance

            with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (True, "OK")
                mock_limiter.record_send = AsyncMock()
                mock_get_limiter.return_value = mock_limiter

                with patch("src.config.get_settings") as mock_get_settings:
                    mock_get_settings.return_value = mock_settings(allow_real_sends=True)

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
        metadata = call_args[0][1]
        assert "sent_at" in metadata  # metadata with sent_at
        assert "message_id" in metadata
        assert "thread_id" in metadata
        assert call_args[0][2] == "operator@pesti.io"  # approved_by

    @pytest.mark.asyncio
    async def test_metadata_includes_message_ids(self, draft_queue, sample_draft):
        """Metadata should include Gmail message and thread IDs"""
        draft_queue._cache[sample_draft["id"]] = sample_draft

        with patch("src.connectors.gmail.GmailConnector") as MockGmail:
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_xyz789", "threadId": "thread_abc123"}
            MockGmail.return_value = mock_instance

            with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (True, "OK")
                mock_limiter.record_send = AsyncMock()
                mock_get_limiter.return_value = mock_limiter

                with patch("src.config.get_settings") as mock_get_settings:
                    mock_get_settings.return_value = mock_settings(allow_real_sends=True)

                    with patch.object(draft_queue, "_get_db") as mock_get_db:
                        mock_db = AsyncMock()
                        mock_db.record_draft_send = AsyncMock(return_value=True)
                        mock_get_db.return_value = mock_db

                        result = await draft_queue.send_draft(
                            draft_id=sample_draft["id"],
                            approved_by="operator@pesti.io",
                        )

        assert result["success"] is True
        call_args = mock_db.record_draft_send.call_args
        metadata = call_args[0][1]
        assert metadata["message_id"] == "msg_xyz789"
        assert metadata["thread_id"] == "thread_abc123"
