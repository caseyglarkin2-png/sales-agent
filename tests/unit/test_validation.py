"""Tests for validation agent."""
import pytest

from src.agents.validation import ValidationAgent


@pytest.mark.asyncio
async def test_validation_agent_initialization():
    """Test validation agent initialization."""
    agent = ValidationAgent()
    assert agent.name == "Validation Agent"


@pytest.mark.asyncio
async def test_validation_compliance_check():
    """Test compliance checking."""
    agent = ValidationAgent()
    
    # Body with prohibited term
    bad_body = "I guarantee this will work for your team"
    good_body = "This solution has helped similar teams streamline their workflow. Please unsubscribe if interested"
    
    bad_result = await agent._check_compliance(bad_body)
    good_result = await agent._check_compliance(good_body)
    
    assert bad_result["passed"] is False
    assert good_result["passed"] is False  # Missing unsubscribe
    

@pytest.mark.asyncio
async def test_validation_quality_check():
    """Test quality checking."""
    agent = ValidationAgent()
    
    good_subject = "Quick question about your growth strategy"
    good_body = "Hi Sarah, I came across your company and was impressed. Would you be open to a brief conversation about how we might help accelerate your timeline? Best regards, Alex"
    
    result = await agent._check_quality(good_subject, good_body)
    assert "passed" in result
    assert "issues" in result


@pytest.mark.asyncio
async def test_validation_agent_validate_input():
    """Test validation agent input validation."""
    agent = ValidationAgent()
    
    valid_input = {
        "draft_id": "draft-123",
        "recipient": "prospect@example.com",
        "subject": "Test",
        "body": "Test body"
    }
    
    invalid_input = {"draft_id": "draft-123"}
    
    assert await agent.validate_input(valid_input) is True
    assert await agent.validate_input(invalid_input) is False


@pytest.mark.asyncio
async def test_validation_agent_execute():
    """Test validation agent execution."""
    agent = ValidationAgent()
    
    context = {
        "draft_id": "draft-123",
        "recipient": "prospect@example.com",
        "subject": "Quick follow-up",
        "body": "Hi Sarah, following up on our previous conversation. Are you still interested in exploring this opportunity? Please unsubscribe if not interested."
    }
    
    result = await agent.execute(context)
    
    assert "draft_id" in result
    assert "approval_status" in result
    assert "checks" in result
    assert result["draft_id"] == "draft-123"
