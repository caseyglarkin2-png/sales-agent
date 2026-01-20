"""Tests for prospecting agent."""
import pytest

from src.agents.prospecting import ProspectingAgent
from src.analysis import MessageAnalyzer
from src.connectors.llm import LLMConnector
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_prospecting_agent_initialization():
    """Test prospecting agent initialization."""
    llm = LLMConnector("test-key")
    agent = ProspectingAgent(llm)
    assert agent.name == "Prospecting Agent"


@pytest.mark.asyncio
async def test_message_analyzer_extract_intent():
    """Test message intent extraction."""
    message = "Hi, I'm interested in your platform. Would you be open to a call?"
    intents = MessageAnalyzer.extract_intent(message)
    
    assert intents["greeting"] is True
    assert intents["proposal"] is True
    assert intents["question"] is True


@pytest.mark.asyncio
async def test_message_analyzer_score():
    """Test message scoring."""
    high_intent_msg = "Hi, I'm interested in your platform for our team. Can we discuss timeline and budget?"
    low_intent_msg = "Just checking if you got my last email."
    
    high_score = MessageAnalyzer.score_message(high_intent_msg)
    low_score = MessageAnalyzer.score_message(low_intent_msg)
    
    assert high_score > low_score


@pytest.mark.asyncio
async def test_prospecting_agent_validate_input():
    """Test prospecting agent input validation."""
    llm = LLMConnector("test-key")
    agent = ProspectingAgent(llm)
    
    valid_input = {
        "message_id": "123",
        "sender": "test@example.com",
        "subject": "Test",
        "body": "Test body"
    }
    
    invalid_input = {"message_id": "123"}
    
    assert await agent.validate_input(valid_input) is True
    assert await agent.validate_input(invalid_input) is False


@pytest.mark.asyncio
async def test_prospecting_agent_execute():
    """Test prospecting agent execution."""
    llm = LLMConnector("test-key")
    agent = ProspectingAgent(llm)
    
    context = {
        "message_id": "msg-123",
        "sender": "prospect@example.com",
        "subject": "Interested in your platform",
        "body": "Hi, we're interested in discussing partnership opportunities"
    }
    
    result = await agent.execute(context)
    
    assert "message_id" in result
    assert "relevance_score" in result
    assert "action" in result
    assert result["sender"] == "prospect@example.com"
