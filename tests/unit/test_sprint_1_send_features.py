"""Tests for Sprint 1 Send Features: ALLOW_REAL_SENDS flag and Rate Limiting"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.operator_mode import DraftQueue, DraftStatus


@pytest.fixture
def draft_queue():
    """Create a draft queue for testing"""
    return DraftQueue(approval_required=True)


def make_approved_draft(draft_id: str, recipient: str = "test@example.com") -> dict:
    """Factory for creating approved drafts"""
    return {
        "id": draft_id,
        "recipient": recipient,
        "subject": "Test Email",
        "body": "This is a test email. Unsubscribe at http://example.com/unsub",
        "metadata": {
            "body_html": "<p>This is a test email.</p><p>Unsubscribe at http://example.com/unsub</p>",
        },
        "status": DraftStatus.APPROVED.value,
        "approved_by": "operator@pesti.io",
        "approved_at": "2026-01-23T10:00:00",
    }


def mock_settings_full(**kwargs):
    """Create a fully configured mock settings object"""
    defaults = {
        "allow_real_sends": True,
        "max_emails_per_day": 20,
        "max_emails_per_week": 2,
        "google_client_id": "test_id",
        "google_client_secret": "test_secret",
        "google_user_email": "user@example.com",
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


class TestSprintOneFeatures:
    """Test Suite for Sprint 1 Email Send Features - TASK 1.4, 1.5, 1.6"""

    @pytest.mark.asyncio
    async def test_task_1_4_feature_flag_blocks_send(self, draft_queue):
        """TASK 1.4: ALLOW_REAL_SENDS=False blocks send"""
        draft = make_approved_draft("send_blocked")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full(allow_real_sends=False)

            result = await draft_queue.send_draft(
                draft_id=draft["id"],
                approved_by="operator@pesti.io",
            )

        assert result["success"] is False
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_1_4_feature_flag_allows_send(self, draft_queue):
        """TASK 1.4: ALLOW_REAL_SENDS=True allows send"""
        draft = make_approved_draft("send_allowed")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full(allow_real_sends=True)

            with patch("src.connectors.gmail.GmailConnector") as MockGmail:
                mock_instance = AsyncMock()
                mock_instance.send_email.return_value = {"id": "msg_123", "threadId": "thread_456"}
                MockGmail.return_value = mock_instance

                with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                    mock_limiter = AsyncMock()
                    mock_limiter.check_can_send.return_value = (True, "OK")
                    mock_limiter.record_send = AsyncMock()
                    mock_get_limiter.return_value = mock_limiter

                    result = await draft_queue.send_draft(
                        draft_id=draft["id"],
                        approved_by="operator@pesti.io",
                    )

        assert result["success"] is True
        assert "message_id" in result

    @pytest.mark.asyncio
    async def test_task_1_6_daily_rate_limit_enforced(self, draft_queue):
        """TASK 1.6: Daily rate limit blocks send"""
        draft = make_approved_draft("daily_limit_test")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full()

            with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (False, "Daily limit (20) reached")
                mock_get_limiter.return_value = mock_limiter

                result = await draft_queue.send_draft(
                    draft_id=draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "daily" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_1_6_contact_weekly_limit_enforced(self, draft_queue):
        """TASK 1.6: Contact weekly rate limit blocks send"""
        draft = make_approved_draft("contact_weekly_test")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full()

            with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                mock_limiter = AsyncMock()
                mock_limiter.check_can_send.return_value = (False, "Contact weekly limit (2) reached")
                mock_get_limiter.return_value = mock_limiter

                result = await draft_queue.send_draft(
                    draft_id=draft["id"],
                    approved_by="operator@pesti.io",
                )

        assert result["success"] is False
        assert "rate limit" in result["error"].lower()
        assert "contact" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_task_1_6_rate_limit_recorded_on_success(self, draft_queue):
        """TASK 1.6: Rate limiter records send after success"""
        draft = make_approved_draft("rate_record_test")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full()

            with patch("src.connectors.gmail.GmailConnector") as MockGmail:
                mock_instance = AsyncMock()
                mock_instance.send_email.return_value = {"id": "msg_456", "threadId": "thread_789"}
                MockGmail.return_value = mock_instance

                with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                    mock_limiter = AsyncMock()
                    mock_limiter.check_can_send.return_value = (True, "OK")
                    mock_limiter.record_send = AsyncMock()
                    mock_get_limiter.return_value = mock_limiter

                    result = await draft_queue.send_draft(
                        draft_id=draft["id"],
                        approved_by="operator@pesti.io",
                    )

        assert result["success"] is True
        # Verify rate limiter recorded usage
        mock_get_limiter.return_value.record_send.assert_called_once_with(draft["recipient"])

    @pytest.mark.asyncio
    async def test_task_1_5_sent_status_persisted(self, draft_queue):
        """TASK 1.5: Draft marked SENT and metadata persisted to database"""
        draft = make_approved_draft("sent_status_test")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full()

            with patch("src.connectors.gmail.GmailConnector") as MockGmail:
                mock_instance = AsyncMock()
                mock_instance.send_email.return_value = {"id": "msg_db1", "threadId": "thread_db1"}
                MockGmail.return_value = mock_instance

                with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                    mock_limiter = AsyncMock()
                    mock_limiter.check_can_send.return_value = (True, "OK")
                    mock_limiter.record_send = AsyncMock()
                    mock_get_limiter.return_value = mock_limiter

                    with patch.object(draft_queue, "_get_db") as mock_get_db:
                        mock_db = AsyncMock()
                        mock_db.record_draft_send = AsyncMock(return_value=True)
                        mock_get_db.return_value = mock_db

                        result = await draft_queue.send_draft(
                            draft_id=draft["id"],
                            approved_by="operator@pesti.io",
                        )

        assert result["success"] is True
        # Verify status updated in memory
        updated_draft = await draft_queue.get_draft(draft["id"])
        assert updated_draft["status"] == DraftStatus.SENT.value
        # Verify persisted to database
        mock_get_db.return_value.record_draft_send.assert_called_once()
        call_args = mock_get_db.return_value.record_draft_send.call_args
        metadata = call_args[0][1]
        assert "sent_at" in metadata
        assert metadata["message_id"] == "msg_db1"
        assert metadata["thread_id"] == "thread_db1"
        assert call_args[0][2] == "operator@pesti.io"

    @pytest.mark.asyncio
    async def test_integration_all_guards_together(self, draft_queue):
        """Integration: All Sprint 1 guards work together (flag + rate limit + status)"""
        draft = make_approved_draft("integration_test", recipient="customer@example.com")
        draft_queue._cache[draft["id"]] = draft

        with patch("src.config.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings_full(allow_real_sends=True)

            with patch("src.connectors.gmail.GmailConnector") as MockGmail:
                mock_instance = AsyncMock()
                mock_instance.send_email.return_value = {"id": "msg_int", "threadId": "thread_int"}
                MockGmail.return_value = mock_instance

                with patch("src.rate_limiter.get_rate_limiter") as mock_get_limiter:
                    mock_limiter = AsyncMock()
                    mock_limiter.check_can_send.return_value = (True, "OK")
                    mock_limiter.record_send = AsyncMock()
                    mock_get_limiter.return_value = mock_limiter

                    with patch.object(draft_queue, "_get_db") as mock_get_db:
                        mock_db = AsyncMock()
                        mock_db.record_draft_send = AsyncMock(return_value=True)
                        mock_get_db.return_value = mock_db

                        result = await draft_queue.send_draft(
                            draft_id=draft["id"],
                            approved_by="operator@pesti.io",
                            require_safety_checks=True,
                        )

        # Verify complete flow executed successfully
        assert result["success"] is True
        assert result["message_id"] == "msg_int"

        # Verify each guard was applied:
        # 1. Rate limiter checked (not blocked)
        mock_get_limiter.return_value.check_can_send.assert_called_once_with("customer@example.com")
        # 2. Rate limiter usage recorded
        mock_get_limiter.return_value.record_send.assert_called_once_with("customer@example.com")
        # 3. Status persisted to database
        mock_get_db.return_value.record_draft_send.assert_called_once()

        # Verify in-memory state updated
        updated_draft = await draft_queue.get_draft(draft["id"])
        assert updated_draft["status"] == DraftStatus.SENT.value
        assert "message_id" in updated_draft["metadata"]
        assert "sent_at" in updated_draft["metadata"]
