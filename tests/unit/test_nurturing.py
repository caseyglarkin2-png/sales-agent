"""Tests for nurturing agent."""
import pytest
from unittest.mock import AsyncMock

from src.agents.nurturing import NurturingAgent
from src.connectors.hubspot import HubSpotConnector


@pytest.mark.asyncio
async def test_nurturing_agent_initialization():
    """Test nurturing agent initialization."""
    hubspot = HubSpotConnector("test-key")
    agent = NurturingAgent(hubspot)
    assert agent.name == "Nurturing Agent"


@pytest.mark.asyncio
async def test_nurturing_agent_get_next_action():
    """Test determining next action by stage."""
    action_initial = NurturingAgent._get_next_action("initial_contact")
    action_engaged = NurturingAgent._get_next_action("engaged")
    action_qualified = NurturingAgent._get_next_action("qualified")
    
    assert "Initial Introduction" in action_initial["title"]
    assert "Deeper Engagement" in action_engaged["title"]
    assert "Demo" in action_qualified["title"]


@pytest.mark.asyncio
async def test_nurturing_agent_calculate_follow_up():
    """Test follow-up date calculation."""
    from datetime import datetime, timedelta
    
    date_initial = NurturingAgent._calculate_follow_up_date("initial_contact")
    date_qualified = NurturingAgent._calculate_follow_up_date("qualified")
    
    now = datetime.utcnow()
    
    # Initial should be ~3 days out
    assert (date_initial - now).days == 3
    # Qualified should be ~2 days out (sooner follow-up)
    assert (date_qualified - now).days == 2


@pytest.mark.asyncio
async def test_nurturing_agent_validate_input():
    """Test nurturing agent input validation."""
    hubspot = HubSpotConnector("test-key")
    agent = NurturingAgent(hubspot)
    
    valid_input = {
        "contact_id": "contact-123",
        "company_id": "company-456",
        "engagement_stage": "engaged"
    }
    
    invalid_input = {"contact_id": "contact-123"}
    
    assert await agent.validate_input(valid_input) is True
    assert await agent.validate_input(invalid_input) is False
