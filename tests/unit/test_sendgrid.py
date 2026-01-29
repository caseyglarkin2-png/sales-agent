"""Unit tests for SendGrid connector and email router.

Sprint 64: SendGrid Integration
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.sendgrid import (
    SendGridConnector,
    SendGridResponse,
    create_sendgrid_connector,
)
from src.services.email_router import (
    EmailRouter,
    EmailProvider,
    EmailResult,
)


class TestSendGridConnector:
    """Tests for SendGrid connector."""

    def test_not_configured_without_api_key(self):
        """Test connector reports not configured without API key."""
        with patch("src.connectors.sendgrid.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sendgrid_api_key="",
                sendgrid_sender_email="",
                sendgrid_sender_name="CaseyOS",
            )
            
            connector = SendGridConnector()
            
            assert not connector.is_configured

    def test_configured_with_api_key(self):
        """Test connector reports configured with API key and email."""
        with patch("src.connectors.sendgrid.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sendgrid_api_key="SG.test_key",
                sendgrid_sender_email="casey@example.com",
                sendgrid_sender_name="CaseyOS",
            )
            
            connector = SendGridConnector()
            
            assert connector.is_configured

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self):
        """Test send returns error when not configured."""
        with patch("src.connectors.sendgrid.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sendgrid_api_key="",
                sendgrid_sender_email="",
                sendgrid_sender_name="",
            )
            
            connector = SendGridConnector()
            result = await connector.send_email(
                to_email="test@example.com",
                subject="Test",
                body_text="Test body",
            )
            
            assert not result.success
            assert "not configured" in result.error.lower()

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email send."""
        with patch("src.connectors.sendgrid.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                sendgrid_api_key="SG.test_key",
                sendgrid_sender_email="casey@example.com",
                sendgrid_sender_name="CaseyOS",
            )
            
            connector = SendGridConnector()
            
            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_response.headers = {"X-Message-Id": "msg123"}
                
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(post=AsyncMock(return_value=mock_response))
                )
                mock_client.return_value.__aexit__ = AsyncMock()
                
                result = await connector.send_email(
                    to_email="recipient@example.com",
                    subject="Test Subject",
                    body_text="Test body content",
                )
                
                assert result.success
                assert result.message_id == "msg123"

    def test_response_dataclass(self):
        """Test SendGridResponse dataclass."""
        response = SendGridResponse(
            success=True,
            message_id="msg123",
            status_code=202,
        )
        
        assert response.success is True
        assert response.message_id == "msg123"
        assert response.error is None


class TestEmailRouter:
    """Tests for email router service."""

    def test_email_result_to_dict(self):
        """Test EmailResult serialization."""
        result = EmailResult(
            success=True,
            provider="gmail",
            message_id="msg123",
            thread_id="thread456",
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["provider"] == "gmail"
        assert data["message_id"] == "msg123"
        assert data["thread_id"] == "thread456"

    def test_email_provider_enum(self):
        """Test EmailProvider enum values."""
        assert EmailProvider.GMAIL.value == "gmail"
        assert EmailProvider.SENDGRID.value == "sendgrid"
        assert EmailProvider.AUTO.value == "auto"

    def test_router_default_provider(self):
        """Test router uses default provider from settings."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            router = EmailRouter()
            
            # Default is gmail
            assert router.default_provider == EmailProvider.GMAIL

    def test_select_provider_prefers_sendgrid_at_limit(self):
        """Test auto-select prefers SendGrid near Gmail limit."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.get_sendgrid_connector") as mock_sg:
                mock_sg.return_value = MagicMock(is_configured=True)
                
                router = EmailRouter()
                router._daily_gmail_count = 450  # 90% of 500 limit
                
                selected = router._select_provider()
                
                assert selected == EmailProvider.SENDGRID

    def test_select_provider_uses_gmail_when_sendgrid_not_configured(self):
        """Test auto-select falls back to Gmail when SendGrid not configured."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.get_sendgrid_connector") as mock_sg:
                mock_sg.return_value = MagicMock(is_configured=False)
                
                router = EmailRouter()
                router._daily_gmail_count = 450
                
                selected = router._select_provider()
                
                # Should fall back to Gmail since SendGrid not configured
                assert selected == EmailProvider.GMAIL

    @pytest.mark.asyncio
    async def test_send_via_gmail(self):
        """Test sending via Gmail provider."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.create_gmail_connector") as mock_gmail:
                mock_connector = MagicMock()
                mock_connector.send_email = AsyncMock(return_value={
                    "message_id": "gmail123",
                    "thread_id": "thread456",
                })
                mock_gmail.return_value = mock_connector
                
                router = EmailRouter()
                result = await router._send_via_gmail(
                    to_email="test@example.com",
                    subject="Test",
                    body_text="Test body",
                )
                
                assert result.success
                assert result.provider == "gmail"
                assert result.message_id == "gmail123"

    @pytest.mark.asyncio
    async def test_send_via_gmail_error(self):
        """Test Gmail send error handling."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.create_gmail_connector") as mock_gmail:
                mock_connector = MagicMock()
                mock_connector.send_email = AsyncMock(side_effect=Exception("Gmail API error"))
                mock_gmail.return_value = mock_connector
                
                router = EmailRouter()
                result = await router._send_via_gmail(
                    to_email="test@example.com",
                    subject="Test",
                    body_text="Test body",
                )
                
                assert not result.success
                assert result.provider == "gmail"
                assert "Gmail API error" in result.error

    @pytest.mark.asyncio
    async def test_send_via_sendgrid(self):
        """Test sending via SendGrid provider."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.get_sendgrid_connector") as mock_sg:
                mock_connector = MagicMock()
                mock_connector.is_configured = True
                mock_connector.send_email = AsyncMock(return_value=SendGridResponse(
                    success=True,
                    message_id="sg123",
                    status_code=202,
                ))
                mock_sg.return_value = mock_connector
                
                router = EmailRouter()
                result = await router._send_via_sendgrid(
                    to_email="test@example.com",
                    subject="Test",
                    body_text="Test body",
                )
                
                assert result.success
                assert result.provider == "sendgrid"
                assert result.message_id == "sg123"

    @pytest.mark.asyncio
    async def test_send_via_sendgrid_not_configured(self):
        """Test SendGrid send when not configured."""
        with patch("src.services.email_router.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(email_provider="gmail")
            
            with patch("src.services.email_router.get_sendgrid_connector") as mock_sg:
                mock_connector = MagicMock()
                mock_connector.is_configured = False
                mock_sg.return_value = mock_connector
                
                router = EmailRouter()
                result = await router._send_via_sendgrid(
                    to_email="test@example.com",
                    subject="Test",
                    body_text="Test body",
                )
                
                assert not result.success
                assert "not configured" in result.error.lower()
