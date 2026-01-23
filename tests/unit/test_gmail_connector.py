"""Tests for Gmail connector OAuth token management and email sending."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from googleapiclient.errors import HttpError

from src.connectors.gmail import GmailConnector


@pytest.mark.asyncio
async def test_refresh_token_when_expired():
    """Test token refresh when credentials are expired."""
    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.token = "old_token"
    mock_creds.refresh = MagicMock()
    
    connector = GmailConnector(credentials=mock_creds, user_email="test@example.com")
    
    with patch.object(connector, '_save_token', new=AsyncMock()):
        result = await connector.refresh_token_if_needed()
    
    assert result is True
    mock_creds.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token_when_expiring_soon():
    """Test token refresh when expiry is within 5 minutes."""
    mock_creds = MagicMock()
    mock_creds.expired = False
    mock_creds.expiry = datetime.utcnow() + timedelta(minutes=3)  # Expires in 3 min
    mock_creds.refresh = MagicMock()
    
    connector = GmailConnector(credentials=mock_creds, user_email="test@example.com")
    
    with patch.object(connector, '_save_token', new=AsyncMock()):
        result = await connector.refresh_token_if_needed()
    
    assert result is True
    mock_creds.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token_not_needed():
    """Test no refresh when token is valid and not expiring soon."""
    mock_creds = MagicMock()
    mock_creds.expired = False
    mock_creds.expiry = datetime.utcnow() + timedelta(hours=1)  # Valid for 1 hour
    mock_creds.refresh = MagicMock()
    
    connector = GmailConnector(credentials=mock_creds, user_email="test@example.com")
    
    result = await connector.refresh_token_if_needed()
    
    assert result is True
    mock_creds.refresh.assert_not_called()


@pytest.mark.asyncio
async def test_refresh_token_failure():
    """Test handling of token refresh failure."""
    mock_creds = MagicMock()
    mock_creds.expired = True
    mock_creds.refresh = MagicMock(side_effect=Exception("Refresh failed"))
    
    connector = GmailConnector(credentials=mock_creds, user_email="test@example.com")
    
    result = await connector.refresh_token_if_needed()
    
    assert result is False


@pytest.mark.asyncio
async def test_send_email_success():
    """Test successful email sending with MIME message."""
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {
        "id": "msg-123",
        "threadId": "thread-456",
        "labelIds": ["SENT"],
    }
    
    connector = GmailConnector()
    connector.service = mock_service
    connector.refresh_token_if_needed = AsyncMock(return_value=True)
    
    result = await connector.send_email(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Test Email",
        body_text="This is a test",
    )
    
    assert result is not None
    assert result["id"] == "msg-123"
    assert result["threadId"] == "thread-456"
    # Verify the API was called (send().execute() chain)
    mock_service.users().messages().send().execute.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_with_html_and_threading():
    """Test email sending with HTML body and threading headers."""
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {
        "id": "msg-789",
        "threadId": "thread-456",
    }
    
    connector = GmailConnector()
    connector.service = mock_service
    connector.refresh_token_if_needed = AsyncMock(return_value=True)
    
    result = await connector.send_email(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Re: Previous conversation",
        body_text="Plain text version",
        body_html="<p>HTML version</p>",
        in_reply_to="<original-123@company.com>",
        references="<original-123@company.com>",
    )
    
    assert result is not None
    assert result["id"] == "msg-789"


@pytest.mark.asyncio
async def test_send_email_retry_on_rate_limit():
    """Test retry logic on rate limit error (429)."""
    mock_response = MagicMock()
    mock_response.status = 429
    
    http_error = HttpError(resp=mock_response, content=b'{"error": {"message": "Rate limit"}}')
    
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.side_effect = [
        http_error,  # First attempt fails
        {"id": "msg-retry", "threadId": "thread-retry"},  # Second attempt succeeds
    ]
    
    connector = GmailConnector()
    connector.service = mock_service
    connector.refresh_token_if_needed = AsyncMock(return_value=True)
    
    result = await connector.send_email(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Retry Test",
        body_text="Testing retry",
        max_retries=3,
    )
    
    assert result is not None
    assert result["id"] == "msg-retry"
    assert mock_service.users().messages().send().execute.call_count == 2


@pytest.mark.asyncio
async def test_send_email_non_retryable_error():
    """Test non-retryable error (400 Bad Request) fails immediately."""
    mock_response = MagicMock()
    mock_response.status = 400
    
    http_error = HttpError(resp=mock_response, content=b'{"error": {"message": "Bad request"}}')
    
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.side_effect = http_error
    
    connector = GmailConnector()
    connector.service = mock_service
    connector.refresh_token_if_needed = AsyncMock(return_value=True)
    
    with pytest.raises(HttpError):
        await connector.send_email(
            from_email="alex@pesti.io",
            to_email="invalid",
            subject="Bad Request Test",
            body_text="This will fail",
        )
    
    # Should only try once for non-retryable error
    assert mock_service.users().messages().send().execute.call_count == 1


@pytest.mark.asyncio
async def test_send_email_max_retries_exhausted():
    """Test failure after max retries exhausted."""
    mock_response = MagicMock()
    mock_response.status = 503  # Server error (retryable)
    
    http_error = HttpError(resp=mock_response, content=b'{"error": {"message": "Server error"}}')
    
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.side_effect = http_error
    
    connector = GmailConnector()
    connector.service = mock_service
    connector.refresh_token_if_needed = AsyncMock(return_value=True)
    
    with pytest.raises(HttpError):
        await connector.send_email(
            from_email="alex@pesti.io",
            to_email="prospect@company.com",
            subject="Max Retry Test",
            body_text="Will fail after retries",
            max_retries=3,
        )
    
    # Should try max_retries times
    assert mock_service.users().messages().send().execute.call_count == 3


@pytest.mark.asyncio
async def test_token_refresh_before_send():
    """Test that token is refreshed before sending email."""
    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {
        "id": "msg-123",
        "threadId": "thread-456",
    }
    
    connector = GmailConnector()
    connector.service = mock_service
    
    # Mock refresh to track if it's called
    refresh_called = []
    async def mock_refresh():
        refresh_called.append(True)
        return True
    
    connector.refresh_token_if_needed = mock_refresh
    
    await connector.send_email(
        from_email="alex@pesti.io",
        to_email="prospect@company.com",
        subject="Refresh Test",
        body_text="Testing token refresh",
    )
    
    assert len(refresh_called) == 1, "Token refresh should be called before send"


@pytest.mark.asyncio
async def test_token_expiring_soon():
    """Test _token_expiring_soon method."""
    mock_creds = MagicMock()
    
    # Test: Token expires in 3 minutes (should return True)
    mock_creds.expiry = datetime.utcnow() + timedelta(minutes=3)
    connector = GmailConnector(credentials=mock_creds)
    assert connector._token_expiring_soon(threshold_minutes=5) is True
    
    # Test: Token expires in 10 minutes (should return False)
    mock_creds.expiry = datetime.utcnow() + timedelta(minutes=10)
    assert connector._token_expiring_soon(threshold_minutes=5) is False
    
    # Test: No expiry set (should return False)
    mock_creds.expiry = None
    assert connector._token_expiring_soon() is False
