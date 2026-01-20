"""Tests for demo agent."""
import pytest

from src.agents.demo import DemoAgent


@pytest.mark.asyncio
async def test_demo_agent_initialization():
    """Test demo agent initialization."""
    agent = DemoAgent()
    assert agent.name == "Demo Agent"


@pytest.mark.asyncio
async def test_demo_agent_prospecting_demo():
    """Test prospecting demo generation."""
    agent = DemoAgent()
    
    result = await agent.execute({
        "demo_type": "prospecting",
        "company_domain": "example.com"
    })
    
    assert result["demo_type"] == "prospecting"
    assert "scenario" in result
    assert "incoming_message" in result["scenario"]


@pytest.mark.asyncio
async def test_demo_agent_validation_demo():
    """Test validation demo generation."""
    agent = DemoAgent()
    
    result = await agent.execute({
        "demo_type": "validation",
        "company_domain": "example.com"
    })
    
    assert result["demo_type"] == "validation"
    assert "scenario" in result
    assert "draft" in result["scenario"]


@pytest.mark.asyncio
async def test_demo_agent_nurturing_demo():
    """Test nurturing demo generation."""
    agent = DemoAgent()
    
    result = await agent.execute({
        "demo_type": "nurturing",
        "company_domain": "example.com"
    })
    
    assert result["demo_type"] == "nurturing"
    assert "scenario" in result


@pytest.mark.asyncio
async def test_demo_agent_validate_input():
    """Test demo agent input validation."""
    agent = DemoAgent()
    
    valid_input = {
        "demo_type": "prospecting",
        "company_domain": "example.com"
    }
    
    invalid_input = {"demo_type": "prospecting"}
    
    assert await agent.validate_input(valid_input) is True
    assert await agent.validate_input(invalid_input) is False
