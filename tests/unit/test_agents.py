"""Tests for base agent class."""
import pytest

from src.agents.base import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    async def execute(self, context):
        """Mock execute."""
        return {"result": "success"}

    async def validate_input(self, context):
        """Mock validate."""
        return True


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Test agent initialization."""
    agent = MockAgent("test-agent", "A test agent")
    assert agent.name == "test-agent"
    assert agent.description == "A test agent"


@pytest.mark.asyncio
async def test_agent_execute():
    """Test agent execution."""
    agent = MockAgent("test-agent", "A test agent")
    result = await agent.execute({})
    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_agent_validate_input():
    """Test agent input validation."""
    agent = MockAgent("test-agent", "A test agent")
    is_valid = await agent.validate_input({})
    assert is_valid is True
