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


# Tests will be added in Sprint 2
# Placeholder structure for now
