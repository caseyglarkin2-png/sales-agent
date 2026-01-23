"""Tests for voice command parsing in Jarvis approval system."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import json


@pytest.fixture
def sample_commands():
    """Sample voice commands for testing parser."""
    return [
        ("Approve this", "approve", None),
        ("Reject this draft", "reject", None),
        ("What's the subject?", "request_info", "subject_only"),
        ("Give me a preview", "request_info", "preview"),
        ("Read the full email", "request_info", "full"),
        ("Show me the next one", "skip", None),
    ]


@pytest.fixture
def mock_gpt4_parser():
    """Mock GPT-4 command parser responses."""
    def _create_mock_response(action, detail_level=None):
        response = MagicMock()
        response.choices = [MagicMock()]
        parsed = {"action": action}
        if detail_level:
            parsed["metadata"] = {"detail_level": detail_level}
        response.choices[0].message.content = json.dumps(parsed)
        return response
    
    return _create_mock_response


# Smoke tests to validate fixtures
def test_sample_commands_fixture_structure(sample_commands):
    """Validate sample_commands fixture has proper structure."""
    assert len(sample_commands) == 6
    # Each command is (text, action, detail_level)
    for cmd in sample_commands:
        assert len(cmd) == 3
        assert isinstance(cmd[0], str)  # Command text
        assert isinstance(cmd[1], str)  # Action
        # detail_level can be None or str


def test_mock_gpt4_parser_fixture(mock_gpt4_parser):
    """Validate mock_gpt4_parser creates proper response structure."""
    mock_response = mock_gpt4_parser("approve", None)
    assert hasattr(mock_response, 'choices')
    assert len(mock_response.choices) > 0
    
    # Test with detail level
    mock_response = mock_gpt4_parser("request_info", "subject_only")
    content = json.loads(mock_response.choices[0].message.content)
    assert "metadata" in content
    assert content["metadata"]["detail_level"] == "subject_only"


# Additional tests will be added in Sprint 2

