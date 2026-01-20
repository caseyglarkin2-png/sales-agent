"""Tests for outcome reporter agent."""
import pytest

from src.agents.outcome_reporter import OutcomeReporterAgent


@pytest.mark.asyncio
async def test_outcome_reporter_initialization():
    """Test outcome reporter initialization."""
    agent = OutcomeReporterAgent()
    assert agent.name == "Outcome Reporter"


@pytest.mark.asyncio
async def test_outcome_reporter_engagement_summary():
    """Test engagement summary generation."""
    agent = OutcomeReporterAgent()
    
    result = await agent.execute({
        "report_type": "engagement_summary",
        "time_period": "2026-01-01 to 2026-01-31"
    })
    
    assert result["report_type"] == "engagement_summary"
    assert "metrics" in result
    assert "open_rate" in result["metrics"]


@pytest.mark.asyncio
async def test_outcome_reporter_conversion_funnel():
    """Test conversion funnel generation."""
    agent = OutcomeReporterAgent()
    
    result = await agent.execute({
        "report_type": "conversion_funnel",
        "time_period": "2026-01-01 to 2026-01-31"
    })
    
    assert result["report_type"] == "conversion_funnel"
    assert "funnel_stages" in result
    assert "conversion_rates" in result


@pytest.mark.asyncio
async def test_outcome_reporter_agent_performance():
    """Test agent performance report generation."""
    agent = OutcomeReporterAgent()
    
    result = await agent.execute({
        "report_type": "agent_performance",
        "time_period": "2026-01-01 to 2026-01-31"
    })
    
    assert result["report_type"] == "agent_performance"
    assert "agents" in result
    assert "prospecting_agent" in result["agents"]


@pytest.mark.asyncio
async def test_outcome_reporter_validate_input():
    """Test outcome reporter input validation."""
    agent = OutcomeReporterAgent()
    
    valid_input = {
        "report_type": "engagement_summary",
        "time_period": "2026-01"
    }
    
    invalid_input = {"report_type": "engagement_summary"}
    
    assert await agent.validate_input(valid_input) is True
    assert await agent.validate_input(invalid_input) is False
