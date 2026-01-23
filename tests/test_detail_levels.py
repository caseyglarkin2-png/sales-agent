"""Tests for detail level functionality in voice approval system."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_draft():
    """Sample draft for testing detail levels."""
    return {
        "id": "test-draft-456",
        "recipient": "sarah@example.com",
        "subject": "Demo Invitation",
        "body": "Hi Sarah,\n\nWould you like to see a demo of our platform?\n\nBest,\nCasey"
    }


# Smoke test to validate fixture structure
def test_mock_draft_fixture_structure(mock_draft):
    """Validate mock_draft fixture has required fields."""
    assert "id" in mock_draft
    assert "recipient" in mock_draft
    assert "subject" in mock_draft
    assert "body" in mock_draft
    assert mock_draft["recipient"] == "sarah@example.com"


# Additional tests will be added in Sprint 2

