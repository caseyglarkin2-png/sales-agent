"""Tests for connectors."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.connectors.gmail import GmailConnector
from src.connectors.hubspot import HubSpotConnector
from src.connectors.llm import LLMConnector


@pytest.mark.asyncio
async def test_gmail_connector_initialization():
    """Test Gmail connector initialization."""
    connector = GmailConnector()
    assert connector.credentials is None
    assert connector.service is None


@pytest.mark.asyncio
async def test_hubspot_connector_initialization():
    """Test HubSpot connector initialization."""
    connector = HubSpotConnector("test-api-key")
    assert connector.api_key == "test-api-key"
    assert "Authorization" in connector.headers


@pytest.mark.asyncio
async def test_llm_connector_initialization():
    """Test LLM connector initialization."""
    connector = LLMConnector("test-api-key")
    assert connector.model == "gpt-4-turbo-preview"


@pytest.mark.asyncio
async def test_gmail_get_messages_returns_list():
    """Test get_messages returns a list."""
    connector = GmailConnector()
    # Mock the service
    connector.service = MagicMock()
    connector.service.users().messages().list().execute.return_value = {"messages": []}
    
    messages = await connector.get_messages()
    assert isinstance(messages, list)
