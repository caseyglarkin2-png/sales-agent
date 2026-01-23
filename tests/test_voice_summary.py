"""Tests for voice summary generation in Jarvis approval system."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.voice_approval import get_voice_approval


@pytest.fixture
def mock_draft():
    """Sample draft for testing voice summary generation."""
    return {
        "id": "test-draft-123",
        "recipient": "john@techcorp.com",
        "company_name": "TechCorp",
        "subject": "Q1 Supply Chain Meeting",
        "body": """Hi John,

I wanted to reach out regarding your supply chain optimization initiatives. Our platform has helped companies like yours reduce logistics costs by 30%.

Would you be open to a 15-minute call next week to discuss?

Best,
Casey

Book time: https://meetings.hubspot.com/casey-larkin""",
        "metadata": {
            "campaign_id": "chainge_na_2026",
            "voice_profile": "casey_larkin"
        }
    }


@pytest.fixture
def mock_gpt4_client(monkeypatch):
    """Mock OpenAI GPT-4 client to avoid API calls in tests."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This email discusses supply chain optimization and requests a call."
    
    mock_create = AsyncMock(return_value=mock_response)
    
    return mock_create


# Tests will be added in Sprint 1B
# Placeholder structure for now
