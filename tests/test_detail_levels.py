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


# Tests will be added in Sprint 2
# Placeholder structure for now
